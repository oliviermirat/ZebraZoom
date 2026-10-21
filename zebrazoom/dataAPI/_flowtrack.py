"""
_flowtrack.py - offline multi-fish tracking with minimum-cost flow (Google OR-Tools).

This is the algorithm behind the "OrTools" post-processing (configuration file:
"OrTools": 1), adapted from the standalone "flowtrack" demo. It is called by
dataAPI.trackWithOrTools(), which feeds it the YOLO boxes recorded during the
tracking and writes the resulting tracks back into the results file.

No deep learning happens in this file. YOLO (deep learning) runs *before*
it and produces boxes with confidence scores; everything below is classic
optimisation that decides which boxes belong to which fish.

How it works (see OrToolsTrackingGuide.md for the long version)
---------------------------------------------------------------
  YOLO detections recorded during the tracking (low threshold, e.g. conf >= 0.01)
      |
      v
  LEVEL 1  min-cost flow over *detections* ("connect the dots")
      - Every box is a dot. The solver draws lines through the dots, one
        line per fish, over a window of ~2000 frames at once.
      - Confident boxes are rewarded, weak boxes cost little, jumps cost
        a lot, starting/ending a line in open water is expensive, and two
        lines may pass through the same (merged) box.
      - The lines are then CUT wherever two fish touch, because who-is-who
        is not reliable there. The remaining pieces are "tracklets".
      |
      v
  LEVEL 2  min-cost flow over *tracklets* ("join the pieces")
      - Joins tracklets into full tracks using direction and speed
        (motion continuity), size, and the length of the gap.
      - This is where identities are decided after fish touch, cross,
        or vanish into deep water and come back (gaps up to ~300 frames).
      - For every join we also compute a *margin*: how much worse the best
        alternative (e.g. swapping two fish) would have been. Small margin
        = ambiguous = flagged in the output.
      |
      v
  GAP FILLING
      - Between two joined tracklets, follow the trail of weak detections
        through the tangle (shortest path); otherwise interpolate short gaps.
        Each box is followed by one fish only, and only at a plausible speed;
        straight lines only where the fish barely moved and lies on a box;
        a gap that cannot be filled plausibly is left empty: no point ever
        "flies" between fish or across empty water.

Main entry point:  track(detections_dataframe, FlowTrackConfig()) -> TrackResult

Libraries: numpy, pandas, and Google OR-Tools (pip install ortools),
which provides the min-cost flow solver (SimpleMinCostFlow). This module is
only imported when the OrTools post-processing runs, so ZebraZoom does not
need OR-Tools otherwise.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field, replace

import numpy as np
import pandas as pd

try:
    from ortools.graph.python import min_cost_flow
except ImportError as e:
    raise ImportError("The OrTools post-processing requires Google OR-Tools, "
                      "install it with: pip install ortools") from e

# =============================================================================
# Parameters
# =============================================================================
# Distances are measured in "sizes": size = sqrt(box_width * box_height) in
# pixels. Using sizes instead of pixels means the same settings work for
# near (big) and deep (small) fish. All costs are dimensionless numbers; only
# their relative values matter.


@dataclass
class Level1Params:
    """Level 1: linking detections frame to frame (min-cost flow over dots)."""

    max_skip: int = 5            # a line may jump over up to this many frames without a box
    max_speed: float = 0.2       # gate: a link is only possible if the move is <= max_speed*gap ...
    gate_slack: float = 0.8      # ... + gate_slack (in sizes). Merged boxes shift centres, hence the slack.
    free_motion: float = 0.2     # movement per frame (sizes) that costs nothing (covers box jitter)
    w_dist: float = 2.0          # cost per size of movement beyond free_motion
    w_size: float = 1.0          # cost per unit of |log(size ratio)| between linked boxes
    w_shape: float = 0.5         # cost per unit of |log(aspect-ratio ratio)| (fish heading differs)
    skip_cost: float = 1.0       # cost per skipped frame
    w_score: float = 0.5         # weight of the score reward (see det_cost())
    p_neutral: float = 0.2       # boxes above this score are rewarded, below it cost a little. YOLO often fires
                                 # extra, weaker boxes on the same fish: rewarding them creates "ghost" lines that
                                 # shred the real fish's line at the swap test (flowtrack demo: 0.1)
    p_entry: float = 0.4         # a line may only START at a box at least this confident
                                 # (except at the video start / window starts)
    entry_cost: float = 8.0      # starting a line in open water costs this much
    exit_cost: float = 8.0       # ending a line in open water costs this much
    edge_cost: float = 0.5       # cheap start/end at the video start/end and at window edges
    border_cost: float = 1.0     # cheaper start/end near the image border
    border_margin: float = 1.0   # "near the border" = box edge within this many sizes of the image edge
    allow_share: bool = True     # let 2 fish pass through 1 (merged) box
    share_cost: float = 0.05     # cost per frame for the 2nd fish in a shared box
    swap_margin: float = 1.0     # a step is "ambiguous" if swapping it with another line's step
                                 # costs less extra than this; lines are cut there
    min_tracklet: int = 5        # pieces shorter than this, cut on both sides, are dissolved
                                 # (their boxes are only used to follow the trail later)
    trim_score: float = 0.1      # boxes weaker than this at both ends of a piece are cut off: a line that lost
                                 # its fish often lingers on junk boxes before ending (0 = off)
    contact_dist: float = 0.0    # optional extra rule: also cut where two used boxes are closer than
                                 # this many sizes (0 = off; the swap test usually suffices)


@dataclass
class Level2Params:
    """Level 2: joining tracklets (min-cost flow over pieces)."""

    max_gap: int = 300            # join pieces separated by up to this many frames
    max_speed: float = 0.15       # gate: straight-line move across a gap <= max_speed*gap ...
    gate_slack: float = 1.5       # ... + gate_slack (sizes)
    vel_frames: int = 15          # frames used to estimate direction/speed at a piece's ends
    damping: float = 40.0         # frames: how quickly "keeps going the same way" fades out
    sigma0: float = 0.15          # expected position error across a very short gap (sizes)
    sigma_per_frame: float = 0.03 # extra expected error per frame of gap (sizes)
    short_sigma_mult: float = 1.5 # pieces shorter than 3 boxes: velocity unknown, be more tolerant
    w_motion: float = 1.0         # weight of the position (extrapolation) error
    w_vel: float = 1.0            # weight of the velocity mismatch (same direction and speed?)
    sigma_vel0: float = 0.015     # expected velocity difference across a short gap (sizes/frame)
    sigma_vel_per_frame: float = 0.001  # ... growing with the gap (fish turn), so it fades for long gaps
    max_motion_cost: float = 25.0 # cap on each of the position and velocity costs of a join
    w_gap: float = 0.01           # cost per frame of gap
    w_size: float = 2.0           # cost per unit |log(size ratio)| (bigger fish stay bigger)
    w_shape: float = 1.0          # cost per unit |log(aspect-ratio ratio)|, fading with the gap
    entry_cost: float = 8.0       # a piece starts a brand-new fish
    exit_cost: float = 8.0        # a piece ends a fish for good. A join i -> j is only made if it costs less than
                                  # exit_cost + entry_cost: higher = fewer identity breaks (flowtrack demo: 6 and 6)
    edge_cost: float = 0.5        # start/end at the video start/end
    border_cost: float = 1.0      # start/end near the image border
    ambiguity_margin: float = 3.0 # joins whose best alternative is within this cost get flagged
    confident_gap: int = 50       # joins across longer gaps (fish unseen) are always flagged:
                                  # re-identifying look-alike fish after a long absence is guesswork


@dataclass
class OutputParams:
    fill_gaps: bool = True        # follow weak boxes through tangles between joined pieces
    fill_max_skip: int = 5        # the trail-following may jump over up to this many empty frames (flowtrack demo: 30)
    trail_min_score: float = 0.02 # boxes weaker than this are ignored when following a trail
    max_interp: int = 100         # interpolate (straight line) gaps of up to this many frames between two known
                                  # positions, only if slow enough (interp_max_speed) and, with interp_on_box, only
                                  # where the point lies on a box (flowtrack demo: 30, with no other condition)
    p_confirm: float = 0.5        # keep only tracks with at least one box this confident ...
    min_detections: int = 5       # ... and at least this many own boxes
    trail_reward: float = 0.0     # weight of the box rewards along a trail: with 1, trails make detours (onto other
                                  # fish) to collect confident boxes; with 0 they follow the smoothest chain (demo: 1)
    trail_max_containment: float = 0.6  # a box lying inside a box of a piece of the same frame by more than this
                                  # fraction (of the smaller box) is a duplicate of a fish already followed: it is
                                  # not used for trails (1.0 = off, as in the demo)
    trail_exclusive: bool = True  # each box (and its duplicates) is followed by one trail only, the shortest gaps
                                  # being filled first: two fish never share a trail (demo: False)
    fill_max_speed: float = 0.1   # sizes/frame: trail steps faster than this (+ fill_gate_slack) are not made
                                  # (0 = off, as in the demo). Real cavefish: ~0.03 on average, 0.14 for 99% of frames
    interp_max_speed: float = 0.06  # sizes/frame: the same limit for straight-line interpolation, where there is no box
                                  # to follow at all: only a fish that barely moved (e.g. hidden under another fish) is
                                  # interpolated, a faster gap is left empty (0 = fill_max_speed)
    interp_on_box: bool = True    # an interpolated position across a gap between two pieces is only kept if it lies
                                  # inside a box of that frame (the fish hidden under another one, a weak box...):
                                  # never a point in empty water (demo: off)
    max_fill_step: float = 0.15   # sizes/frame: final guard, walking along each track, any filled row (trail, shared or
                                  # interpolated) farther than this (+ fill_gate_slack) from the previous row shown is
                                  # removed: no filled point can ever move fast (0 = off, as in the demo)
    max_own_step: float = 0.4     # sizes/frame: same guard on the track's own boxes: where they jump farther than this
                                  # (+ fill_gate_slack), faster than a fish swims (a line that switched to a touching
                                  # fish), the track is split in two instead of showing a jump (0 = off, as in the demo;
                                  # only active when max_fill_step is on)
    fill_gate_slack: float = 0.1  # sizes, tolerance (box jitter) added to the three speed limits above


@dataclass
class FlowTrackConfig:
    level1: Level1Params = field(default_factory=Level1Params)
    level2: Level2Params = field(default_factory=Level2Params)
    output: OutputParams = field(default_factory=OutputParams)
    frame_size: tuple[int, int] | None = None  # (width, height) in px; inferred from boxes if None
    window: int = 2000            # frames per level-1 window
    overlap: int = 200            # overlap between consecutive level-1 windows
    cost_scale: int = 1000        # OR-Tools needs integer costs: cost_int = round(cost * cost_scale)
    size_cue: str = "diagonal"    # what level1.w_size and level2.w_size compare between boxes: "diagonal" = box
                                  # diagonal, close to the fish length whatever its orientation; "area" =
                                  # sqrt(width*height), which changes when an elongated fish turns (demo: "area")
    verbose: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "FlowTrackConfig":
        d = dict(d)
        cfg = cls()
        for key, sub in (("level1", cfg.level1), ("level2", cfg.level2), ("output", cfg.output)):
            for k, v in d.pop(key, {}).items():
                if not hasattr(sub, k):
                    raise KeyError(f"unknown parameter {key}.{k}")
                setattr(sub, k, v)
        for k, v in d.items():
            if not hasattr(cfg, k):
                raise KeyError(f"unknown parameter {k}")
            setattr(cfg, k, tuple(v) if k == "frame_size" and v is not None else v)
        return cfg


@dataclass
class TrackResult:
    tracks: pd.DataFrame      # one row per (frame, track): box, score, source, uncertain
    links: pd.DataFrame       # every level-2 join with its cost and margin
    summary: pd.DataFrame     # one row per track
    tracklets: pd.DataFrame   # level-1 pieces (for debugging)
    stats: dict


# =============================================================================
# Small helpers
# =============================================================================

def _logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def det_cost(score, p: Level1Params):
    """Cost of using a box (negative = reward).

    -w_score * (logit(score) - logit(p_neutral)), with the defaults:
      score 0.9  -> about -1.8 (strong reward)
      score 0.5  -> about -0.7
      score 0.2  ->  0        (p_neutral)
      score 0.05 -> about +0.8 (weak boxes cost a little)
    Weak boxes must stay cheap, otherwise a fish crossing a tangle of weak boxes
    would rather "end and restart"; but they should not be a big reward either,
    otherwise lines get pulled onto long chains of drifting debris.
    """
    return -p.w_score * (_logit(score) - _logit(p.p_neutral))


def _fit_line(t, x):
    """Least-squares line x(t). Returns (slope, mean_t, mean_x)."""
    t = np.asarray(t, float)
    x = np.asarray(x, float)
    tm, xm = t.mean(), x.mean(axis=0)
    dt = t - tm
    denom = float((dt * dt).sum())
    if denom <= 0:
        return np.zeros_like(xm), tm, xm
    slope = (dt[:, None] * (x - xm)).sum(axis=0) / denom
    return slope, tm, xm


def _log(cfg, *msg):
    if cfg.verbose:
        print("[OrTools]", *msg, flush=True)


class _Detections:
    """Detections sorted by frame, with the derived quantities we need."""

    def __init__(self, df: pd.DataFrame, cfg: FlowTrackConfig):
        need = {"frame", "x1", "y1", "x2", "y2", "score"}
        missing = need - set(df.columns)
        if missing:
            raise ValueError(f"detections are missing columns: {sorted(missing)}")
        df = df.sort_values(["frame", "score"], ascending=[True, False], kind="stable")
        self.orig_index = df.index.to_numpy()          # row index in the caller's DataFrame
        df = df.reset_index(drop=True)
        self.df = df
        self.frame = df["frame"].to_numpy(np.int64)
        x1, y1 = df["x1"].to_numpy(float), df["y1"].to_numpy(float)
        x2, y2 = df["x2"].to_numpy(float), df["y2"].to_numpy(float)
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        self.w = np.maximum(x2 - x1, 1.0)
        self.h = np.maximum(y2 - y1, 1.0)
        self.cx = (x1 + x2) / 2
        self.cy = (y1 + y2) / 2
        self.size = np.sqrt(self.w * self.h)
        self.length = np.hypot(self.w, self.h) if cfg.size_cue == "diagonal" else self.size   # for the w_size terms
        self.log_ar = np.log(self.w / self.h)          # box shape: wide (fish horizontal) vs tall
        self.score = np.clip(df["score"].to_numpy(float), 0.0, 1.0)
        self.n = len(df)
        self.cdet = det_cost(self.score, cfg.level1)
        if cfg.frame_size is None:
            W, H = float(x2.max()), float(y2.max())
        else:
            W, H = map(float, cfg.frame_size)
        self.frame_size = (W, H)
        m = cfg.level1.border_margin * self.size
        edge = np.minimum.reduce([x1, y1, W - x2, H - y2])
        self.near_border = edge < m
        self.first_frame = int(self.frame.min()) if self.n else 0
        self.last_frame = int(self.frame.max()) if self.n else 0

    def range(self, t0, t1):
        """Indices of detections with t0 <= frame < t1 (contiguous, since sorted)."""
        lo = np.searchsorted(self.frame, t0, "left")
        hi = np.searchsorted(self.frame, t1, "left")
        return lo, hi


# =============================================================================
# The min-cost flow solver (used by level 1 AND level 2)
# =============================================================================

def solve_min_cost_paths(n_nodes, node_cost, entry_idx, entry_cost, exit_idx, exit_cost,
                         arc_src, arc_dst, arc_cost, arc_cap=1,
                         share_cost=None, share_cap=0, cost_scale=1000):
    """Find the cheapest set of non-overlapping paths through a set of nodes.

    Nodes are detections (level 1) or tracklets (level 2). Each node i is split
    into u_i -> v_i so that it can carry at most 1 path (+ share_cap extra
    paths at share_cost each). Graph:

        S -> u_i            start a path at node i   (entry_cost)
        u_i -> v_i          use node i               (node_cost, negative = reward)
        v_a -> u_b          link a to b              (arc_cost)
        v_i -> T            end a path at node i     (exit_cost)
        S -> T              "bypass": unused flow, cost 0

    With N units of flow sent from S to T and the free bypass, the solver
    automatically decides how many paths to draw: a path is only drawn if its
    total cost is negative, i.e. worth it. This gives the global optimum over
    the whole window at once (not frame by frame).

    Returns node_flow, arc_flow, entry_flow, exit_flow (integer numpy arrays).
    """
    node_cost = np.asarray(node_cost, float)
    entry_idx = np.asarray(entry_idx, np.int64)
    exit_idx = np.asarray(exit_idx, np.int64)
    arc_src = np.asarray(arc_src, np.int64)
    arc_dst = np.asarray(arc_dst, np.int64)
    n_arcs = len(arc_src)
    S, T = 0, 1
    u = 2 + 2 * np.arange(n_nodes, dtype=np.int64)
    v = u + 1
    N = int(len(entry_idx))
    if N == 0 or n_nodes == 0:
        z = np.zeros(n_nodes, np.int64)
        return z, np.zeros(n_arcs, np.int64), np.zeros(len(entry_idx), np.int64), np.zeros(len(exit_idx), np.int64)

    def as_int(c):
        return np.round(np.asarray(c, float) * cost_scale).astype(np.int64)

    parts = []  # (tails, heads, caps, costs)
    parts.append((u, v, np.ones(n_nodes, np.int64), as_int(node_cost)))
    has_share = share_cap > 0 and share_cost is not None
    if has_share:
        parts.append((u, v, np.full(n_nodes, share_cap, np.int64), as_int(np.full(n_nodes, share_cost))))
    parts.append((np.full(len(entry_idx), S, np.int64), u[entry_idx],
                  np.ones(len(entry_idx), np.int64), as_int(entry_cost)))
    parts.append((v[exit_idx], np.full(len(exit_idx), T, np.int64),
                  np.ones(len(exit_idx), np.int64), as_int(exit_cost)))
    cap = np.broadcast_to(np.asarray(arc_cap, np.int64), (n_arcs,)).copy()
    parts.append((v[arc_src], u[arc_dst], cap, as_int(arc_cost)))
    parts.append((np.array([S]), np.array([T]), np.array([N]), np.array([0])))

    tails = np.concatenate([p[0] for p in parts])
    heads = np.concatenate([p[1] for p in parts])
    caps = np.concatenate([p[2] for p in parts])
    costs = np.concatenate([p[3] for p in parts])

    smcf = min_cost_flow.SimpleMinCostFlow()
    arcs = smcf.add_arcs_with_capacity_and_unit_cost(tails, heads, caps, costs)
    supplies = np.zeros(2 + 2 * n_nodes, np.int64)
    supplies[S], supplies[T] = N, -N
    smcf.set_nodes_supplies(np.arange(len(supplies), dtype=np.int64), supplies)
    status = smcf.solve()
    if status != smcf.OPTIMAL:
        raise RuntimeError(f"min-cost flow failed with status {status}")
    flows = np.asarray(smcf.flows(arcs), np.int64)

    k = 0
    node_flow = flows[k:k + n_nodes].copy(); k += n_nodes
    if has_share:
        node_flow += flows[k:k + n_nodes]; k += n_nodes
    entry_flow = flows[k:k + len(entry_idx)]; k += len(entry_idx)
    exit_flow = flows[k:k + len(exit_idx)]; k += len(exit_idx)
    arc_flow = flows[k:k + n_arcs]
    return node_flow, arc_flow, entry_flow, exit_flow


# =============================================================================
# Level 1: detections -> tracklets
# =============================================================================

def link_cost(D: _Detections, a, b, p: Level1Params, max_skip=None):
    """Level-1 cost of linking box a to a later box b (elementwise over arrays).

    Returns (cost, ok): ok is False where the link is impossible (too far,
    wrong time order, or too many skipped frames).
    """
    a = np.asarray(a, np.int64)
    b = np.asarray(b, np.int64)
    max_skip = p.max_skip if max_skip is None else max_skip
    g = (D.frame[b] - D.frame[a]).astype(float)
    sa, sb = D.size[a], D.size[b]
    dist = np.hypot(D.cx[b] - D.cx[a], D.cy[b] - D.cy[a])
    ok = (g >= 1) & (g <= max_skip + 1) & (dist <= np.maximum(sa, sb) * (p.max_speed * g + p.gate_slack))
    c = (p.w_dist * np.maximum(0.0, dist / (0.5 * (sa + sb)) - p.free_motion * g)
         + p.skip_cost * (g - 1) + p.w_size * np.abs(np.log(D.length[b] / D.length[a]))
         + p.w_shape * np.abs(D.log_ar[b] - D.log_ar[a]))
    return c, ok


def _level1_links(D: _Detections, lo, hi, p: Level1Params):
    """Candidate links between detections in [lo, hi) (local indices)."""
    src, dst, cost = [], [], []
    frames = D.frame[lo:hi]
    uniq = np.unique(frames)
    # start/end index of each frame inside the window (local)
    starts = np.searchsorted(frames, uniq, "left")
    ends = np.searchsorted(frames, uniq, "right")
    pos = {int(f): (int(a), int(b)) for f, a, b in zip(uniq, starts, ends)}
    for f, (a0, a1) in pos.items():
        A = np.arange(a0, a1) + lo
        for g in range(1, p.max_skip + 2):
            if f + g not in pos:
                continue
            b0, b1 = pos[f + g]
            B = np.arange(b0, b1) + lo
            dx = D.cx[B][None, :] - D.cx[A][:, None]
            dy = D.cy[B][None, :] - D.cy[A][:, None]
            dist = np.hypot(dx, dy)
            sa, sb = D.size[A][:, None], D.size[B][None, :]
            s_mean = 0.5 * (sa + sb)
            ok = dist <= np.maximum(sa, sb) * (p.max_speed * g + p.gate_slack)
            if not ok.any():
                continue
            d_norm = dist / s_mean
            c = (p.w_dist * np.maximum(0.0, d_norm - p.free_motion * g)
                 + p.skip_cost * (g - 1)
                 + p.w_size * np.abs(np.log(D.length[B][None, :] / D.length[A][:, None]))
                 + p.w_shape * np.abs(D.log_ar[B][None, :] - D.log_ar[A][:, None]))
            ia, ib = np.nonzero(ok)
            src.append(A[ia] - lo)
            dst.append(B[ib] - lo)
            cost.append(c[ia, ib])
    if not src:
        return np.zeros(0, np.int64), np.zeros(0, np.int64), np.zeros(0)
    return np.concatenate(src), np.concatenate(dst), np.concatenate(cost)


def _level1_window(D: _Detections, ws, we, cfg: FlowTrackConfig):
    """Solve level 1 on frames [ws, we). Returns local results."""
    p = cfg.level1
    lo, hi = D.range(ws, we)
    n = hi - lo
    if n == 0:
        return lo, hi, np.zeros(0, np.int64), (np.zeros(0, np.int64),) * 3
    f = D.frame[lo:hi]
    score = D.score[lo:hi]
    border = D.near_border[lo:hi]
    edge_frames = p.max_skip + 1
    near_start = f < ws + edge_frames
    near_end = f >= we - edge_frames

    ent = np.full(n, np.inf)
    strong = score >= p.p_entry
    ent[strong] = p.entry_cost
    ent[strong & border] = p.border_cost
    ent[near_start] = np.minimum(ent[near_start], p.edge_cost)   # any score: lines continuing from before
    entry_idx = np.flatnonzero(np.isfinite(ent))

    ext = np.full(n, p.exit_cost)
    ext[border] = np.minimum(ext[border], p.border_cost)
    ext[near_end] = np.minimum(ext[near_end], p.edge_cost)
    exit_idx = np.arange(n)

    a_src, a_dst, a_cost = _level1_links(D, lo, hi, p)
    share_cap = 1 if p.allow_share else 0
    node_flow, arc_flow, _, _ = solve_min_cost_paths(
        n, D.cdet[lo:hi], entry_idx, ent[entry_idx], exit_idx, ext[exit_idx],
        a_src, a_dst, a_cost, arc_cap=1 + share_cap,
        share_cost=p.share_cost, share_cap=share_cap, cost_scale=cfg.cost_scale)
    return lo, hi, node_flow, (a_src, a_dst, arc_flow)


def _ambiguous_steps(D: _Detections, lo, a_src, a_dst, a_flow, p: Level1Params):
    """Mark links where two lines could swap their next step almost for free.

    For two used links a1->b1 and a2->b2 that overlap in time, compare with the
    swapped version a1->b2, a2->b1. If the swap costs less than swap_margin
    extra, the solver's choice there is close to a coin flip, so both links
    are cut and level 2 decides with direction/speed over longer pieces.
    """
    amb = np.zeros(len(a_src), bool)
    use = np.flatnonzero(a_flow >= 1)
    if len(use) < 2:
        return amb
    s_g, d_g = a_src[use] + lo, a_dst[use] + lo
    fs, fd = D.frame[s_g], D.frame[d_g]
    own, _ = link_cost(D, s_g, d_g, p)
    order = np.argsort(fs, kind="stable")
    fs_sorted = fs[order]
    G = p.max_skip + 1
    for k in range(len(use)):
        # partner links that start before this one ends, and end after this one starts
        lo_k = np.searchsorted(fs_sorted, fs[k] - G, "left")
        hi_k = np.searchsorted(fs_sorted, fd[k] - 1, "right")
        cand = order[lo_k:hi_k]
        cand = cand[(cand > k) & (fd[cand] > fs[k]) & (s_g[cand] != s_g[k]) & (d_g[cand] != d_g[k])]
        if not len(cand):
            continue
        c1, ok1 = link_cost(D, np.full(len(cand), s_g[k]), d_g[cand], p)
        c2, ok2 = link_cost(D, s_g[cand], np.full(len(cand), d_g[k]), p)
        ok = ok1 & ok2
        if not ok.any():
            continue
        delta = c1 + c2 - own[k] - own[cand]
        hit = cand[ok & (delta < p.swap_margin)]
        if len(hit):
            amb[use[k]] = True
            amb[use[hit]] = True
    return amb


def _tracklets_from_window(D: _Detections, lo, hi, node_flow, arcs, cs, ce, p: Level1Params):
    """Cut the level-1 lines into tracklets inside the window core [cs, ce).

    Lines are cut (1) at boxes shared by two fish (merged boxes), (2) at steps
    where two lines could swap almost for free (see _ambiguous_steps), and
    optionally (3) where two used boxes are closer than contact_dist sizes.
    Shared/contact boxes are kept aside for gap filling.
    """
    a_src, a_dst, a_flow = arcs
    n = hi - lo
    f = D.frame[lo:hi]
    in_core = (f >= cs) & (f < ce)
    used = node_flow >= 1
    contact = node_flow >= 2
    if p.contact_dist > 0:
        # optional: proximity contacts among used boxes, frame by frame
        used_idx = np.flatnonzero(used & in_core)
        if len(used_idx):
            bounds = np.flatnonzero(np.diff(f[used_idx])) + 1
            for grp in np.split(used_idx, bounds):
                if len(grp) < 2:
                    continue
                g = grp + lo
                dist = np.hypot(D.cx[g][:, None] - D.cx[g][None, :], D.cy[g][:, None] - D.cy[g][None, :])
                lim = p.contact_dist * np.maximum(D.size[g][:, None], D.size[g][None, :])
                close = dist < lim
                np.fill_diagonal(close, False)
                contact[grp[close.any(axis=1)]] = True
    ambiguous = _ambiguous_steps(D, lo, a_src, a_dst, a_flow, p)

    member = used & ~contact & (node_flow == 1) & in_core
    nxt = np.full(n, -1, np.int64)
    prv = np.full(n, -1, np.int64)
    clean = (a_flow == 1) & ~ambiguous & member[a_src] & member[a_dst]
    nxt[a_src[clean]] = a_dst[clean]
    prv[a_dst[clean]] = a_src[clean]

    # For each box, the (unique) used link arriving at / leaving it, if any.
    used_arc = np.flatnonzero(a_flow >= 1)
    in_arc = np.full(n, -1, np.int64)
    out_arc = np.full(n, -1, np.int64)
    in_arc[a_dst[used_arc]] = used_arc
    out_arc[a_src[used_arc]] = used_arc

    def cut_at(arc, other_end):
        # the line continues through `arc` but was cut there because of a tangle
        # (not because of a window boundary or a genuine start/end)
        return arc >= 0 and in_core[other_end] and (ambiguous[arc] or not member[other_end])

    tracklets = []
    for h in np.flatnonzero(member & (prv == -1)):
        chain = [h]
        while nxt[chain[-1]] >= 0:
            chain.append(nxt[chain[-1]])
        t = chain[-1]
        ia, oa = in_arc[h], out_arc[t]
        cut_before = cut_at(ia, a_src[ia]) if ia >= 0 else False
        cut_after = cut_at(oa, a_dst[oa]) if oa >= 0 else False
        if len(chain) < p.min_tracklet and cut_before and cut_after:
            contact[chain] = True          # too short to carry direction/speed: dissolve
            continue
        tracklets.append(np.asarray(chain, np.int64) + lo)
    contact_ids = np.flatnonzero(used & contact & in_core) + lo
    shared_ids = np.flatnonzero((node_flow >= 2) & in_core) + lo
    return tracklets, contact_ids, shared_ids


def run_level1(D: _Detections, cfg: FlowTrackConfig):
    """Level 1 over the whole video, window by window."""
    t_first, t_last = D.first_frame, D.last_frame + 1
    core = max(cfg.window - cfg.overlap, 1)
    half = cfg.overlap // 2
    tracklets, contact_ids, shared_ids = [], [], []
    cs = t_first
    k = 0
    while cs < t_last:
        ce = min(cs + core, t_last)
        if t_last - ce < core // 4:   # avoid a tiny last window
            ce = t_last
        ws = max(t_first, cs - half)
        we = min(t_last, ce + half)
        t0 = time.time()
        lo, hi, node_flow, arcs = _level1_window(D, ws, we, cfg)
        tr, cid, sid = _tracklets_from_window(D, lo, hi, node_flow, arcs, cs, ce, cfg.level1)
        tracklets += tr
        contact_ids.append(cid)
        shared_ids.append(sid)
        k += 1
        _log(cfg, f"level 1 window {k}: frames {ws}-{we - 1}, {hi - lo} boxes, "
                  f"{len(arcs[0])} links, {len(tr)} tracklets, {time.time() - t0:.1f}s")
        cs = ce
    contact_ids = np.concatenate(contact_ids) if contact_ids else np.zeros(0, np.int64)
    shared_ids = np.concatenate(shared_ids) if shared_ids else np.zeros(0, np.int64)
    return tracklets, contact_ids, shared_ids


# =============================================================================
# Level 1 only: the raw lines, before any cut (to look at what level 1 does)
# =============================================================================

def _window_lines(D: _Detections, lo, node_flow, arcs):
    """Split the flow of one level-1 window into its lines (arrays of box ids, in time order).

    The flow gives how many lines pass through each box and each link, not which line is which where two lines
    share a box: there, each line continues on the next box closest to where its own motion points.
    """
    a_src, a_dst, a_flow = arcs
    n = len(node_flow)
    used = np.flatnonzero(a_flow >= 1)
    inflow = np.bincount(a_dst[used], weights=a_flow[used], minlength=n)
    starts = np.round(node_flow - inflow).astype(np.int64)      # lines starting at each box (flow conservation)
    order = used[np.argsort(a_src[used], kind="stable")]
    first = np.searchsorted(a_src[order], np.arange(n + 1))    # used links leaving box i: order[first[i]:first[i + 1]]
    left = a_flow.astype(np.int64)
    lines = []
    for i in np.flatnonzero(starts > 0):                       # (boxes are sorted by frame)
        for _ in range(starts[i]):
            line, prev, cur = [i], None, i
            while True:
                out = order[first[cur]:first[cur + 1]]
                out = out[left[out] > 0]
                if not len(out):
                    break                                       # the line ends here
                g = cur + lo
                vx = vy = 0.0
                if prev is not None:
                    dt = D.frame[g] - D.frame[prev + lo]
                    vx, vy = (D.cx[g] - D.cx[prev + lo]) / dt, (D.cy[g] - D.cy[prev + lo]) / dt
                dst = a_dst[out] + lo
                gap = D.frame[dst] - D.frame[g]
                err = np.hypot(D.cx[dst] - (D.cx[g] + vx * gap), D.cy[dst] - (D.cy[g] + vy * gap))
                k = out[int(np.argmin(err))]
                left[k] -= 1
                prev, cur = cur, int(a_dst[k])
                line.append(cur)
            lines.append(np.asarray(line, np.int64) + lo)
    return lines


def run_level1_lines(D: _Detections, cfg: FlowTrackConfig):
    """Level 1 over the whole video, window by window as in run_level1, but with no cut at all.

    Each line is kept on the core frames of its window; a line going on into the next window is chained to the
    line of the next window that passes through the same box (the windows overlap). Returns the lines (arrays of
    box ids) and the boxes shared by two lines.
    """
    t_first, t_last = D.first_frame, D.last_frame + 1
    core = max(cfg.window - cfg.overlap, 1)
    half = cfg.overlap // 2
    lines, shared_ids, handover = [], [], {}
    cs = t_first
    k = 0
    while cs < t_last:
        ce = min(cs + core, t_last)
        if t_last - ce < core // 4:   # avoid a tiny last window
            ce = t_last
        ws = max(t_first, cs - half)
        we = min(t_last, ce + half)
        t0 = time.time()
        lo, hi, node_flow, arcs = _level1_window(D, ws, we, cfg)
        f = D.frame[lo:hi]
        shared_ids.append(np.flatnonzero((node_flow >= 2) & (f >= cs) & (f < ce)) + lo)
        next_handover = {}
        n_new = 0
        for ids in _window_lines(D, lo, node_flow, arcs):
            fr = D.frame[ids]
            part = ids[(fr >= cs) & (fr < ce)]
            if not len(part):
                continue
            previous = handover.get(int(part[0]))
            if previous:                                        # continues a line of the previous window
                idx = previous.pop(0)
                lines[idx] = np.concatenate([lines[idx], part])
            else:
                lines.append(part)
                idx = len(lines) - 1
                n_new += 1
            after = ids[fr >= ce]
            if len(after):
                next_handover.setdefault(int(after[0]), []).append(idx)
        handover = next_handover
        k += 1
        _log(cfg, f"level 1 window {k}: frames {ws}-{we - 1}, {hi - lo} boxes, {len(arcs[0])} links, "
                  f"{n_new} new line(s), {time.time() - t0:.1f}s")
        cs = ce
    shared_ids = np.concatenate(shared_ids) if shared_ids else np.zeros(0, np.int64)
    return lines, shared_ids


def track_level1_only(detections: pd.DataFrame, cfg: FlowTrackConfig | None = None) -> TrackResult:
    """Level 1 alone, to look at what it does: the lines drawn by the min-cost flow through the boxes, as they are.

    Nothing after the solver is applied: no cut where two fish touch (swap test, shared boxes, short pieces, end
    trimming), no level 2, no gap filling, no final filtering of the tracks. One track per line; rows on a box that
    two lines pass through are marked "shared"; the frames a line jumps over (missed detections, up to
    level1.max_skip) are left empty. Same columns as track().
    """
    cfg = cfg or FlowTrackConfig()
    t_start = time.time()
    D = _Detections(detections, cfg)
    _log(cfg, f"{D.n} boxes, frames {D.first_frame}-{D.last_frame}, frame size {D.frame_size} (level 1 only)")
    cols = ["track_id", "frame", "x1", "y1", "x2", "y2", "score", "source", "det_index", "uncertain", "id_segment"]
    if D.n == 0:
        empty = pd.DataFrame(columns=cols)
        return TrackResult(empty, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {"n_boxes": 0})
    lines, shared_ids = run_level1_lines(D, cfg)
    shared_set = set(int(x) for x in shared_ids)
    rows = [(tid, int(D.frame[d]), *_row(D, d, "shared" if d in shared_set else "detected"), False, 0)
            for tid, ids in enumerate(lines) for d in ids]
    out = pd.DataFrame(rows, columns=cols)
    first = out.groupby("track_id")["frame"].min().sort_values(kind="stable")
    out["track_id"] = out["track_id"].map({old: new for new, old in enumerate(first.index, start=1)})
    out = out.sort_values(["track_id", "frame"], kind="stable").reset_index(drop=True)
    summary = out.groupby("track_id").agg(first_frame=("frame", "min"), last_frame=("frame", "max"),
                                          n_rows=("frame", "size"), max_score=("score", "max")).reset_index()
    stats = {"n_boxes": int(D.n), "n_lines": len(lines), "n_shared_boxes": int(len(shared_set)),
             "n_tracks": int(out["track_id"].nunique()), "seconds": round(time.time() - t_start, 2)}
    _log(cfg, f"output: {stats['n_tracks']} lines, {stats['n_shared_boxes']} boxes shared by 2 lines, "
              f"total {stats['seconds']}s")
    return TrackResult(out, pd.DataFrame(), summary, pd.DataFrame(), stats)


# =============================================================================
# Level 2: tracklets -> tracks
# =============================================================================

@dataclass
class _Pieces:
    """Per-tracklet features used by level 2."""

    dets: list
    s: np.ndarray
    e: np.ndarray
    pos_s: np.ndarray
    pos_e: np.ndarray
    vel_s: np.ndarray
    vel_e: np.ndarray
    size_s: np.ndarray
    size_e: np.ndarray
    len_s: np.ndarray
    len_e: np.ndarray
    shape_s: np.ndarray
    shape_e: np.ndarray
    n: np.ndarray
    reward: np.ndarray
    max_score: np.ndarray
    border_s: np.ndarray
    border_e: np.ndarray


def _piece_features(D: _Detections, tracklets, p2: Level2Params) -> _Pieces:
    m = len(tracklets)
    s = np.zeros(m, np.int64); e = np.zeros(m, np.int64)
    pos_s = np.zeros((m, 2)); pos_e = np.zeros((m, 2))
    vel_s = np.zeros((m, 2)); vel_e = np.zeros((m, 2))
    size_s = np.zeros(m); size_e = np.zeros(m)
    len_s = np.zeros(m); len_e = np.zeros(m)
    shape_s = np.zeros(m); shape_e = np.zeros(m)
    n = np.zeros(m, np.int64); reward = np.zeros(m); max_score = np.zeros(m)
    border_s = np.zeros(m, bool); border_e = np.zeros(m, bool)
    K = max(p2.vel_frames, 2)
    for i, ids in enumerate(tracklets):
        t = D.frame[ids]
        xy = np.stack([D.cx[ids], D.cy[ids]], axis=1)
        s[i], e[i] = t[0], t[-1]
        n[i] = len(ids)
        reward[i] = D.cdet[ids].sum()
        max_score[i] = D.score[ids].max()
        border_s[i], border_e[i] = D.near_border[ids[0]], D.near_border[ids[-1]]
        # robust end points and velocities from a straight-line fit on K boxes
        head = t <= t[0] + K
        tail = t >= t[-1] - K
        for sel, t0, pos, vel, size_arr, shape_arr, len_arr in ((head, t[0], pos_s, vel_s, size_s, shape_s, len_s),
                                                                (tail, t[-1], pos_e, vel_e, size_e, shape_e, len_e)):
            slope, tm, xm = _fit_line(t[sel], xy[sel])
            if sel.sum() < 3:
                slope = np.zeros(2)
            pos[i] = xm + slope * (t0 - tm)
            vel[i] = slope
            size_arr[i] = np.median(D.size[ids[sel]])
            len_arr[i] = np.median(D.length[ids[sel]])
            shape_arr[i] = np.median(D.log_ar[ids[sel]])
    return _Pieces(tracklets, s, e, pos_s, pos_e, vel_s, vel_e, size_s, size_e, len_s, len_e, shape_s, shape_e,
                   n, reward, max_score, border_s, border_e)


def _level2_links(P: _Pieces, p2: Level2Params):
    """Candidate joins i -> j (j starts after i ends) with their costs."""
    order = np.argsort(P.s, kind="stable")
    s_sorted = P.s[order]
    src, dst, cost = [], [], []
    tau = p2.damping
    for i in range(len(P.s)):
        lo = np.searchsorted(s_sorted, P.e[i], "right")
        hi = np.searchsorted(s_sorted, P.e[i] + p2.max_gap, "right")
        if hi <= lo:
            continue
        J = order[lo:hi]
        g = (P.s[J] - P.e[i]).astype(float)
        size_ref = 0.5 * (P.size_e[i] + P.size_s[J])
        direct = np.hypot(*(P.pos_s[J] - P.pos_e[i]).T) / size_ref
        ok = direct <= p2.max_speed * g + p2.gate_slack
        if not ok.any():
            continue
        J, g, size_ref = J[ok], g[ok], size_ref[ok]
        reach = tau * (1.0 - np.exp(-g / tau))          # damped "keep going" distance factor
        pred_j = P.pos_e[i] + P.vel_e[i] * reach[:, None]      # i pushed forward in time
        back_i = P.pos_s[J] - P.vel_s[J] * reach[:, None]      # j pushed backward in time
        err = 0.5 * (np.hypot(*(pred_j - P.pos_s[J]).T) + np.hypot(*(back_i - P.pos_e[i]).T)) / size_ref
        sigma = p2.sigma0 + p2.sigma_per_frame * g
        short = (P.n[i] < 3) | (P.n[J] < 3)
        sigma = np.where(short, sigma * p2.short_sigma_mult, sigma)
        # the log term makes vague (long-gap) joins cost more than precise ones
        motion = (np.minimum(p2.w_motion * (err / sigma) ** 2, p2.max_motion_cost)
                  + 2.0 * np.log(sigma / p2.sigma0))
        # direction/speed continuity: essential when two fish cross (positions coincide)
        dv = np.hypot(*(P.vel_s[J] - P.vel_e[i]).T) / size_ref
        sigma_v = p2.sigma_vel0 + p2.sigma_vel_per_frame * g
        vel = np.where(short, 0.0, np.minimum(p2.w_vel * (dv / sigma_v) ** 2, p2.max_motion_cost))
        # box shape (heading) changes as fish turn, so its weight fades with the gap
        shape = p2.w_shape * np.abs(P.shape_s[J] - P.shape_e[i]) * np.exp(-g / tau)
        c = (motion + vel + shape + p2.w_gap * g
             + p2.w_size * np.abs(np.log(P.len_s[J] / P.len_e[i])))
        src.append(np.full(len(J), i, np.int64))
        dst.append(J)
        cost.append(c)
    if not src:
        return np.zeros(0, np.int64), np.zeros(0, np.int64), np.zeros(0)
    return np.concatenate(src), np.concatenate(dst), np.concatenate(cost)


def run_level2(D: _Detections, tracklets, cfg: FlowTrackConfig):
    p2 = cfg.level2
    P = _piece_features(D, tracklets, p2)
    m = len(tracklets)
    edge = cfg.level1.max_skip + 1
    ent = np.full(m, p2.entry_cost)
    ent[P.border_s] = np.minimum(ent[P.border_s], p2.border_cost)
    ent[P.s < D.first_frame + edge] = p2.edge_cost
    ext = np.full(m, p2.exit_cost)
    ext[P.border_e] = np.minimum(ext[P.border_e], p2.border_cost)
    ext[P.e > D.last_frame - edge] = p2.edge_cost

    src, dst, cost = _level2_links(P, p2)
    node_flow, arc_flow, entry_flow, _ = solve_min_cost_paths(
        m, P.reward, np.arange(m), ent, np.arange(m), ext, src, dst, cost,
        arc_cap=1, cost_scale=cfg.cost_scale)

    chosen = arc_flow == 1
    nxt = np.full(m, -1, np.int64)
    has_prev = np.zeros(m, bool)
    nxt[src[chosen]] = dst[chosen]
    has_prev[dst[chosen]] = True
    tracks = []
    for h in np.flatnonzero((node_flow == 1) & ~has_prev):
        chain = [h]
        while nxt[chain[-1]] >= 0:
            chain.append(nxt[chain[-1]])
        tracks.append(chain)

    margins = _link_margins(src, dst, cost, chosen, nxt, has_prev, node_flow, ent, ext)
    return P, tracks, (src, dst, cost, chosen, margins)


def _link_margins(src, dst, cost, chosen, nxt, has_prev, node_flow, ent, ext):
    """For each chosen join i->j: how much worse is the best alternative?

    Alternatives checked:
      * swap with another chosen join k->l:  i->l and k->j instead
      * i continues to an unjoined start m instead (j becomes a new fish)
      * an unjoined end k continues to j instead (i ends)
      * no join at all (i ends, j starts a new fish)
    Margin >= 0 because the solution is optimal. Small margin = ambiguous.
    """
    cand = {(int(a), int(b)): float(c) for a, b, c in zip(src, dst, cost)}
    succ, pred = {}, {}
    for (a, b) in cand:
        succ.setdefault(a, []).append(b)
        pred.setdefault(b, []).append(a)
    margins = np.full(len(src), np.nan)
    used = node_flow == 1
    for idx in np.flatnonzero(chosen):
        i, j = int(src[idx]), int(dst[idx])
        c_ij = cand[(i, j)]
        best = ext[i] + ent[j] - c_ij                     # break the join
        for k in pred.get(j, []):                           # someone else continues to j
            if k == i or not used[k]:
                continue
            l = int(nxt[k])
            if l >= 0:
                if (i, l) in cand:
                    best = min(best, cand[(i, l)] + cand[(k, j)] - c_ij - cand[(k, l)])
            else:                                           # k was an end
                best = min(best, cand[(k, j)] + ext[i] - c_ij - ext[k])
        for mm in succ.get(i, []):                          # i continues elsewhere
            if mm == j or not used[mm] or has_prev[mm]:
                continue
            best = min(best, cand[(i, mm)] + ent[j] - c_ij - ent[mm])
        margins[idx] = max(best, 0.0)
    return margins


# =============================================================================
# Gap filling: follow the weak-box trail between two joined tracklets
# =============================================================================

def _trail(D: _Detections, a, b, cand_ids, p1: Level1Params, max_skip, reward=1.0):
    """Cheapest chain of candidate boxes from box a to box b (DAG shortest path).

    Uses the same link costs as level 1. Returns the list of box ids strictly
    between a and b, or None if b cannot be reached.
    """
    nodes = np.concatenate([[a], cand_ids, [b]]).astype(np.int64)
    fr = D.frame[nodes]
    order = np.argsort(fr, kind="stable")
    nodes, fr = nodes[order], fr[order]
    ia = int(np.flatnonzero(nodes == a)[0])
    ib = int(np.flatnonzero(nodes == b)[-1])
    n = len(nodes)
    best = np.full(n, np.inf)
    back = np.full(n, -1, np.int64)
    best[ia] = 0.0
    node_c = D.cdet[nodes].copy()
    node_c = np.where(node_c < 0, node_c * reward, node_c)
    node_c[ib] = 0.0
    for k in range(ia, n):
        if not np.isfinite(best[k]):
            continue
        lo = np.searchsorted(fr, fr[k] + 1, "left")
        hi = np.searchsorted(fr, fr[k] + max_skip + 1, "right")
        if hi <= lo:
            continue
        J = np.arange(lo, hi)
        c, ok = link_cost(D, np.full(len(J), nodes[k]), nodes[J], p1, max_skip=max_skip)
        if not ok.any():
            continue
        J, c = J[ok], c[ok] + node_c[J[ok]]
        new = best[k] + c
        better = new < best[J]
        best[J[better]] = new[better]
        back[J[better]] = k
    if not np.isfinite(best[ib]):
        return None
    path = []
    k = back[ib]
    while k >= 0 and k != ia:
        path.append(int(nodes[k]))
        k = back[k]
    return path[::-1]


def _overlaps(D: _Detections, owned, max_containment):
    """True for the boxes not owned by a piece that overlap an owned box of the same frame by more than
    max_containment of the smaller of the two boxes."""
    out = np.zeros(D.n, bool)
    frames, starts = np.unique(D.frame, return_index=True)
    ends = np.append(starts[1:], D.n)
    for lo, hi in zip(starts, ends):
        idx = np.arange(lo, hi)
        own, cand = idx[owned[idx]], idx[~owned[idx]]
        if not len(own) or not len(cand):
            continue
        iw = np.minimum(D.x2[cand][:, None], D.x2[own][None]) - np.maximum(D.x1[cand][:, None], D.x1[own][None])
        ih = np.minimum(D.y2[cand][:, None], D.y2[own][None]) - np.maximum(D.y1[cand][:, None], D.y1[own][None])
        inter = np.clip(iw, 0, None) * np.clip(ih, 0, None)
        area_c = (D.x2[cand] - D.x1[cand]) * (D.y2[cand] - D.y1[cand])
        area_o = (D.x2[own] - D.x1[own]) * (D.y2[own] - D.y1[own])
        containment = inter / np.minimum(area_c[:, None], area_o[None])
        out[cand[(containment > max_containment).any(axis=1)]] = True
    return out


def _reserve(D: _Detections, d, taken, max_containment):
    """Mark box d, and the boxes of its frame it overlaps by more than max_containment, as taken."""
    lo, hi = D.range(D.frame[d], D.frame[d] + 1)
    idx = np.arange(lo, hi)
    inter = (np.clip(np.minimum(D.x2[d], D.x2[idx]) - np.maximum(D.x1[d], D.x1[idx]), 0, None)
             * np.clip(np.minimum(D.y2[d], D.y2[idx]) - np.maximum(D.y1[d], D.y1[idx]), 0, None))
    area = (D.x2 - D.x1)[idx] * (D.y2 - D.y1)[idx]
    taken[idx[inter / np.minimum(area, (D.x2[d] - D.x1[d]) * (D.y2[d] - D.y1[d])) > min(max_containment, 0.99)]] = True
    taken[d] = True


def _inside_a_box(D: _Detections, out, min_score):
    """For each row of out: is its position inside at least one box (score >= min_score) of the same frame?"""
    cx = ((out["x1"] + out["x2"]) / 2).to_numpy()
    cy = ((out["y1"] + out["y2"]) / 2).to_numpy()
    frame = out["frame"].to_numpy()
    inside = np.zeros(len(out), bool)
    order = np.argsort(frame, kind="stable")
    for idx in np.split(order, np.flatnonzero(np.diff(frame[order])) + 1):
        lo, hi = D.range(frame[idx[0]], frame[idx[0]] + 1)
        b = np.arange(lo, hi)
        b = b[D.score[b] >= min_score]
        if len(b):
            inside[idx] = ((cx[idx, None] >= D.x1[b][None]) & (cx[idx, None] <= D.x2[b][None])
                           & (cy[idx, None] >= D.y1[b][None]) & (cy[idx, None] <= D.y2[b][None])).any(axis=1)
    return inside


def _remove_flying_points(out, max_step, max_own_step, slack):
    """Final guard against "flying" points, walking along each track (distances in track sizes: median size of the
    track's own boxes):
      * a filled row (trail, shared or interpolated) farther than (max_step * frames + slack) from the previous row
        kept is removed;
      * where the track's own boxes ("detected") jump farther than (max_own_step * frames + slack), which a fish
        cannot swim (a line that switched to a touching fish), the track is split there: the rest becomes a new
        track (0 = never split).
    Returns the rows kept and the splits made, as (track_id, first frame of the new track, new track_id)."""
    out = out.sort_values(["track_id", "frame"], kind="stable").reset_index(drop=True)
    cx = ((out["x1"] + out["x2"]) / 2).to_numpy()
    cy = ((out["y1"] + out["y2"]) / 2).to_numpy()
    size = np.sqrt(np.maximum(out["x2"] - out["x1"], 1) * np.maximum(out["y2"] - out["y1"], 1)).to_numpy()
    frame = out["frame"].to_numpy()
    tid = out["track_id"].to_numpy()
    own = (out["source"] == "detected").to_numpy()
    keep = np.ones(len(out), bool)
    new_tid = tid.copy()
    splits = []
    next_id = int(tid.max()) + 1 if len(tid) else 0
    starts = np.flatnonzero(np.r_[True, tid[1:] != tid[:-1]])
    for lo, hi in zip(starts, np.r_[starts[1:], len(out)]):
        ref = np.median(size[lo:hi][own[lo:hi]]) if own[lo:hi].any() else np.median(size[lo:hi])
        last, current = None, tid[lo]
        for i in range(lo, hi):
            dist = np.hypot(cx[i] - cx[last], cy[i] - cy[last]) if last is not None else 0.0
            gap = frame[i] - frame[last] if last is not None else 0
            if own[i]:
                if max_own_step > 0 and last is not None and dist > ref * (max_own_step * gap + slack):
                    splits.append((int(current), int(frame[i]), next_id))   # (chained splits: from the current id)
                    current = next_id
                    next_id += 1
                last = i
            elif last is None or dist > ref * (max_step * gap + slack):
                keep[i] = False
                continue
            else:
                last = i
            new_tid[i] = current
    out = out.assign(track_id=new_tid)
    return out[keep].reset_index(drop=True), splits


def _plausible(b1, b2, gap, max_speed, slack):
    """Is moving from box b1 to box b2 in `gap` frames within the speed limit (sizes/frame, + slack sizes)?"""
    size = 0.5 * (np.sqrt(max(b1[2] - b1[0], 1) * max(b1[3] - b1[1], 1)) + np.sqrt(max(b2[2] - b2[0], 1) * max(b2[3] - b2[1], 1)))
    dist = np.hypot((b2[0] + b2[2] - b1[0] - b1[2]) / 2, (b2[1] + b2[3] - b1[1] - b1[3]) / 2)
    return dist <= size * (max_speed * gap + slack)


def _box_row(D, d):
    return (D.x1[d], D.y1[d], D.x2[d], D.y2[d])


def _row(D, d, source):
    """Output values for box d: x1, y1, x2, y2, score, source, det_index."""
    return (*_box_row(D, d), D.score[d], source, int(D.orig_index[d]))


# =============================================================================
# Main entry point
# =============================================================================

def track(detections: pd.DataFrame, cfg: FlowTrackConfig | None = None) -> TrackResult:
    """Track fish offline from saved detections.

    detections: DataFrame with columns frame (int), x1, y1, x2, y2 (pixels), score.
                Save them from YOLO with a LOW confidence threshold (e.g. 0.01)
                and relaxed NMS (e.g. iou=0.8) so weak boxes are available.
    """
    cfg = cfg or FlowTrackConfig()
    t_start = time.time()
    D = _Detections(detections, cfg)
    _log(cfg, f"{D.n} boxes, frames {D.first_frame}-{D.last_frame}, frame size {D.frame_size}")
    if D.n == 0:
        empty = pd.DataFrame()
        return TrackResult(empty, empty, empty, empty, {"n_boxes": 0})

    # ---- level 1 ------------------------------------------------------------
    tracklets, contact_ids, shared_ids = run_level1(D, cfg)
    if cfg.level1.trim_score > 0:
        trimmed = []
        for ids in tracklets:
            strong = np.flatnonzero(D.score[ids] >= cfg.level1.trim_score)
            if len(strong):
                trimmed.append(ids[strong[0]:strong[-1] + 1])
        tracklets = trimmed
    _log(cfg, f"level 1 done: {len(tracklets)} tracklets, {len(contact_ids)} contact boxes "
              f"({len(shared_ids)} shared by 2 fish)")

    # ---- level 2 ------------------------------------------------------------
    t0 = time.time()
    P, chains, (l_src, l_dst, l_cost, chosen, margins) = run_level2(D, tracklets, cfg)
    _log(cfg, f"level 2 done: {len(chains)} tracks from {len(tracklets)} tracklets, "
              f"{len(l_src)} candidate joins, {time.time() - t0:.1f}s")

    # ---- assemble tracks, fill gaps -------------------------------------------
    t0 = time.time()
    o, p1 = cfg.output, cfg.level1
    # boxes free for trail-following: everything not owned by a tracklet
    owned = np.zeros(D.n, bool)
    for ids in tracklets:
        owned[ids] = True
    free = ~owned & (D.score >= o.trail_min_score)
    if o.trail_max_containment < 1.0:
        free &= ~_overlaps(D, owned, o.trail_max_containment)
    free_ids = np.flatnonzero(free)   # already sorted by frame
    p1_fill = replace(p1, max_speed=o.fill_max_speed, gate_slack=o.fill_gate_slack) if o.fill_max_speed > 0 else p1
    free_frames = D.frame[free_ids]
    shared_set = set(int(x) for x in shared_ids)
    link_lookup = {(int(a), int(b)): k for k, (a, b) in enumerate(zip(l_src, l_dst))}

    rows, link_rows, gaps = [], [], []
    for tid, chain in enumerate(chains):
        segment = 0   # increases after every ambiguous join: (track_id, id_segment) = strict identity
        for pos_in_chain, piece in enumerate(chain):
            ids = P.dets[piece]
            for d in ids:
                rows.append((tid, int(D.frame[d]), *_row(D, d, "detected"), False, segment, False))
            for d1, d2 in zip(ids[:-1], ids[1:]):          # short holes inside a piece
                t1, t2 = int(D.frame[d1]), int(D.frame[d2])
                b1, b2 = np.array(_box_row(D, d1)), np.array(_box_row(D, d2))
                for t in range(t1 + 1, t2):
                    w = (t - t1) / (t2 - t1)
                    rows.append((tid, t, *((1 - w) * b1 + w * b2), np.nan, "interpolated", -1, False, segment, False))
            if pos_in_chain + 1 == len(chain):
                continue
            nxt_piece = chain[pos_in_chain + 1]
            k = link_lookup[(piece, nxt_piece)]
            margin = float(margins[k])
            ambiguous = bool(margin < cfg.level2.ambiguity_margin
                             or P.s[nxt_piece] - P.e[piece] > cfg.level2.confident_gap)
            a = int(P.dets[piece][-1])
            b = int(P.dets[nxt_piece][0])
            fa, fb = int(D.frame[a]), int(D.frame[b])
            link_rows.append((tid, fa, fb, fb - fa, float(l_cost[k]), margin, ambiguous))
            if ambiguous:
                segment += 1
            if fb - fa > 1:
                gaps.append((tid, a, b, fa, fb, ambiguous, segment))

    # ---- fill the gaps between joined pieces ------------------------------------
    # With trail_exclusive, the shortest gaps (most reliable) are filled first and every box a trail uses (with its
    # duplicates) is then reserved for that fish, so that two fish never follow the same boxes (shared boxes excepted).
    taken = np.zeros(D.n, bool)

    def fill(a, b, fa, fb):
        filled = {}
        if o.fill_gaps:
            lo = np.searchsorted(free_frames, fa + 1, "left")
            hi = np.searchsorted(free_frames, fb - 1, "right")
            cand = free_ids[lo:hi]
            cand = cand[~taken[cand]]
            if len(cand):
                # keep only boxes reachable from both ends (a corridor between a and b)
                t_c = D.frame[cand]
                s_ref = 0.5 * (D.size[a] + D.size[b])
                p2 = cfg.level2
                da = np.hypot(D.cx[cand] - D.cx[a], D.cy[cand] - D.cy[a])
                db = np.hypot(D.cx[cand] - D.cx[b], D.cy[cand] - D.cy[b])
                ok = ((da <= s_ref * (p2.max_speed * (t_c - fa) + p2.gate_slack))
                      & (db <= s_ref * (p2.max_speed * (fb - t_c) + p2.gate_slack)))
                if o.fill_max_speed > 0:
                    ok &= ((da <= s_ref * (o.fill_max_speed * (t_c - fa) + o.fill_gate_slack))
                           & (db <= s_ref * (o.fill_max_speed * (fb - t_c) + o.fill_gate_slack)))
                cand = cand[ok]
            path = _trail(D, a, b, cand, p1_fill, o.fill_max_skip, o.trail_reward) if len(cand) else None
            if path is not None:
                for d in path:
                    filled[int(D.frame[d])] = _row(D, d, "shared" if d in shared_set else "trail")
                    if o.trail_exclusive and d not in shared_set:
                        _reserve(D, d, taken, o.trail_max_containment)
        has_trail = bool(filled)
        if has_trail or (fb - fa - 1) <= o.max_interp:
            # interpolate the remaining holes between known boxes
            knots = [(fa, np.array(_box_row(D, a)))]
            knots += [(t, np.array(v[:4], float)) for t, v in sorted(filled.items())]
            knots += [(fb, np.array(_box_row(D, b)))]
            for (t1, b1), (t2, b2) in zip(knots[:-1], knots[1:]):
                if t2 - t1 <= 1 or (t2 - t1 - 1) > o.max_interp:
                    continue
                speed = o.interp_max_speed or o.fill_max_speed
                if speed > 0 and not _plausible(b1, b2, t2 - t1, speed, o.fill_gate_slack):
                    continue
                for t in range(t1 + 1, t2):
                    w = (t - t1) / (t2 - t1)
                    filled[t] = (*((1 - w) * b1 + w * b2), np.nan, "interpolated", -1)
        # (a long gap with no trail is left empty: the fish was not seen)
        return filled

    order = sorted(range(len(gaps)), key=lambda i: gaps[i][4] - gaps[i][3]) if o.trail_exclusive else range(len(gaps))
    for i in order:
        tid, a, b, fa, fb, ambiguous, segment = gaps[i]
        for t, v in fill(a, b, fa, fb).items():
            rows.append((tid, t, *v, ambiguous, segment, True))   # True: fills a gap between two pieces

    cols = ["track_id", "frame", "x1", "y1", "x2", "y2", "score", "source", "det_index",
            "uncertain", "id_segment"]
    out = pd.DataFrame(rows, columns=cols + ["in_gap"])
    # ---- no "flying" points: interpolations across gaps on a box only, then no fast filled row at all ----------
    # (the short holes inside a piece, where YOLO missed the fish for a few frames, are only checked by the guard)
    if o.interp_on_box and len(out):
        across_gap = (out["source"] == "interpolated").to_numpy() & out["in_gap"].to_numpy()
        out = out[~across_gap | _inside_a_box(D, out, o.trail_min_score)].reset_index(drop=True)
    out = out[cols]
    if o.max_fill_step > 0 and len(out):
        out, splits = _remove_flying_points(out, o.max_fill_step, o.max_own_step, o.fill_gate_slack)
    else:
        splits = []
    links = pd.DataFrame(link_rows, columns=["track_id", "from_frame", "to_frame", "gap",
                                             "cost", "margin", "ambiguous"])
    for old_tid, first_frame, new_tid in splits:          # the joins after a split belong to the new track
        links.loc[(links["track_id"] == old_tid) & (links["from_frame"] >= first_frame), "track_id"] = new_tid
    if out.empty:
        _log(cfg, "no tracks found")
        return TrackResult(out, links, pd.DataFrame(), pd.DataFrame(), {"n_boxes": int(D.n)})

    # ---- keep confirmed tracks, renumber ------------------------------------
    det_rows = out[out["source"] == "detected"]
    g = det_rows.groupby("track_id")["score"]
    ok = (g.max() >= o.p_confirm) & (g.size() >= o.min_detections)
    keep = ok[ok].index
    out = out[out["track_id"].isin(keep)].copy()
    links = links[links["track_id"].isin(keep)].copy()
    first = out.groupby("track_id")["frame"].min().sort_values(kind="stable")
    remap = {old: new for new, old in enumerate(first.index, start=1)}
    out["track_id"] = out["track_id"].map(remap)
    links["track_id"] = links["track_id"].map(remap)
    out = out.sort_values(["track_id", "frame"], kind="stable").reset_index(drop=True)
    links = links.sort_values(["track_id", "from_frame"], kind="stable").reset_index(drop=True)

    summary = out.groupby("track_id").agg(
        first_frame=("frame", "min"), last_frame=("frame", "max"), n_rows=("frame", "size"),
        n_detected=("source", lambda s: int((s == "detected").sum())),
        n_trail=("source", lambda s: int(s.isin(["trail", "shared"]).sum())),
        n_interpolated=("source", lambda s: int((s == "interpolated").sum())),
        max_score=("score", "max"))
    if len(links):
        lsum = links.groupby("track_id").agg(n_joins=("gap", "size"),
                                             n_ambiguous_joins=("ambiguous", "sum"),
                                             min_margin=("margin", "min"))
        summary = summary.join(lsum, how="left")
    summary = summary.fillna({"n_joins": 0, "n_ambiguous_joins": 0}).reset_index()

    tl_rows = [(k, int(P.s[k]), int(P.e[k]), int(P.n[k]), float(P.max_score[k])) for k in range(len(P.s))]
    tracklets_df = pd.DataFrame(tl_rows, columns=["tracklet", "first_frame", "last_frame", "n_boxes", "max_score"])
    stats = {
        "n_boxes": int(D.n),
        "n_tracklets": len(tracklets),
        "n_contact_boxes": int(len(contact_ids)),
        "n_shared_boxes": int(len(shared_ids)),
        "n_tracks": int(out["track_id"].nunique()),
        "n_joins": int(len(links)),
        "n_ambiguous_joins": int(links["ambiguous"].sum()) if len(links) else 0,
        "seconds": round(time.time() - t_start, 2),
    }
    _log(cfg, f"output: {stats['n_tracks']} tracks, {stats['n_joins']} joins "
              f"({stats['n_ambiguous_joins']} ambiguous), total {stats['seconds']}s")
    return TrackResult(out, links, summary, tracklets_df, stats)
