import os
import subprocess

import ffmpeg_progress_yield
import static_ffmpeg
static_ffmpeg.add_paths()

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog, QProgressDialog

import zebrazoom.code.util as util


def chooseVideoToTroubleshootSplitVideo(self, controller):

  # Choosing video to split
  self.videoToTroubleshootSplitVideo, _ =  QFileDialog.getOpenFileName(self.window, "Select video", os.path.expanduser("~"), "All files(*)")
  if not self.videoToTroubleshootSplitVideo:
    return

  def beginningAndEndChosen():
    # Choosing directory to save sub-video
    firstFrame = self.configFile["firstFrame"]
    lastFrame = self.configFile["lastFrame"]
    self.configFile = configFile
    _, existingExtension = os.path.splitext(self.videoToTroubleshootSplitVideo)
    filename, _ = QFileDialog.getSaveFileName(controller.window, 'Choose where you want to save the sub-video.', os.path.join(os.path.dirname(self.videoToTroubleshootSplitVideo), f'subvideo{existingExtension}'), f"Video (*{existingExtension})")
    if not filename:
      return

    # Extracting sub-video
    cancelled = False
    progressDialog = QProgressDialog("Saving video...", "Cancel", 0, 100, controller.window, Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
    progressDialog.setWindowTitle('Saving Video')
    progressDialog.setAutoClose(False)
    progressDialog.setAutoReset(False)
    progressDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    progressDialog.setMinimumDuration(500)

    numerator, denominator = map(float, subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v", "-of", "default=noprint_wrappers=1:nokey=1", "-show_entries", "stream=r_frame_rate", self.videoToTroubleshootSplitVideo], universal_newlines=True).split('/'))
    fps = numerator / denominator
    cmd = ffmpeg_progress_yield.FfmpegProgress(["ffmpeg", "-y", "-ss", f"{firstFrame / fps}", "-to", f"{lastFrame / fps}", "-i", self.videoToTroubleshootSplitVideo, "-force_key_frames", "00:00:00", "-c", "copy", filename])
    for pct in cmd.run_command_with_progress():
        if progressDialog.wasCanceled():
          cancelled = True
          cmd.quit_gracefully()
          break
        progressDialog.setValue(int(pct))
    progressDialog.close()
    if not cancelled:
      self.show_frame("VideoToTroubleshootSplitVideo")
    else:
      self.show_frame("ChooseVideoToTroubleshootSplitVideo")

  configFile = self.configFile.copy()
  # User input of beginning and end of subvideo
  util.chooseBeginningPage(self, self.videoToTroubleshootSplitVideo, "Choose where the beginning of your sub-video should be", "Ok, I want the sub-video to start at this frame!",
                           lambda: util.chooseEndPage(self, self.videoToTroubleshootSplitVideo, "Choose where the sub-video should end.", "Ok, I want the sub-video to end at this frame!", beginningAndEndChosen,
                                                      leftButtonInfo=("Go to the start page", lambda: setattr(self, 'configFile', configFile) or self.show_frame("StartPage"))),
                           leftButtonInfo=("Go to the start page", lambda: self.show_frame("StartPage")))
