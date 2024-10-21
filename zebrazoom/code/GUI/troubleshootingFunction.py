import os

import av

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
    filename, _ = QFileDialog.getSaveFileName(controller.window, 'Choose where you want to save the sub-video.', os.path.join(os.path.dirname(self.videoToTroubleshootSplitVideo), 'subvideo.mkv'), "Matroska (*.mkv)")
    if not filename:
      return

    # Extracting sub-video
    cancelled = False
    progressDialog = QProgressDialog("Saving video...", "Cancel", firstFrame, lastFrame, controller.window, Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
    progressDialog.setWindowTitle('Saving Video')
    progressDialog.setAutoClose(False)
    progressDialog.setAutoReset(False)
    progressDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    progressDialog.setMinimumDuration(0)
    frameIdx = None

    with av.open(self.videoToTroubleshootSplitVideo) as container, av.open(filename, 'w') as output:
      instream = container.streams.video[0]

      # Calculate the PTS we have to seek to and seek to the nearest keyframe
      framerate = instream.average_rate
      tb = instream.time_base
      container.seek(round(firstFrame / (framerate * tb)), backward=True, any_frame=False, stream=instream)

      outstream = output.add_stream('libx265', rate=10)
      outstream.width = instream.codec_context.width
      outstream.height = instream.codec_context.height
      outstream.pix_fmt = instream.codec_context.pix_fmt
      outstream.options = {'crf': '22'}
      for frame in container.decode(instream):
        if frameIdx is None:
          frameIdx = int(frame.pts * tb * framerate)  # we cannot know which frame we ended up seeking to in advance, so we need to calculate the index from the pts of the first frame we read
        if frameIdx >= firstFrame:
          progressDialog.setValue(frameIdx)
          progressDialog.setLabelText(f'Saving frame {frameIdx}...')
          output.mux(outstream.encode(av.VideoFrame.from_image(frame.to_image())))
        if frameIdx == lastFrame:
          break
        if progressDialog.wasCanceled():
          cancelled = True
          break
        frameIdx += 1
      progressDialog.setLabelText('Saving video...')
      output.mux(outstream.encode(None))
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
