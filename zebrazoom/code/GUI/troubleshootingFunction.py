import os
import subprocess

import cv2
import ffmpeg_progress_yield
import static_ffmpeg
static_ffmpeg.add_paths()

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog, QProgressDialog

import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import zebrazoom.code.util as util


def _runLegacy(inputPath, outputPath, progressDialog, firstFrame, lastFrame):
    cap = zzVideoReading.VideoCapture(inputPath)
    if not cap.isOpened():
      print("Error opening video stream or file")
      return
    cap.set(1, firstFrame)
    width = int(cap.get(3))
    height = int(cap.get(4))

    out = cv2.VideoWriter(outputPath, cv2.VideoWriter_fourcc(*'MJPG'), 10, (width, height))
    for frameIdx in range(firstFrame, lastFrame):
      progressDialog.setValue(frameIdx)
      progressDialog.setLabelText(f'Saving frame {frameIdx}...')
      ret, frame = cap.read()
      if not ret:
        print(f"Error reading at frame {frameIdx}")
        break
      frameHeight, frameWidth = frame.shape[:2]
      if frameHeight < height or frameWidth < width:
        xOffset = (width - frameWidth) // 2
        yOffset = (height - frameHeight) // 2
        copy = cv2.resize(frame, (width, height))
        copy[:] = 0
        copy[yOffset:yOffset+frameHeight, xOffset:xOffset+frameWidth] = frame
        frame = copy
      out.write(frame)
      if progressDialog.wasCanceled():
        cancelled = True
        break
    progressDialog.setLabelText('Saving video...')
    cap.release()
    out.release()
    progressDialog.close()


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
    specialFormat = existingExtension in ('.sqb', '.seq', '.tif', '.tiff', '.bias')
    if specialFormat:
      existingExtension = '.avi'
    filename, _ = QFileDialog.getSaveFileName(controller.window, 'Choose where you want to save the sub-video.', os.path.join(os.path.dirname(self.videoToTroubleshootSplitVideo), f'subvideo{existingExtension}'), f"Video (*{existingExtension})")
    if not filename:
      return

    # Extracting sub-video
    cancelled = False
    progressDialog = QProgressDialog("Saving video...", "Cancel", firstFrame if specialFormat else 0, lastFrame if specialFormat else 100, controller.window, Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
    progressDialog.setWindowTitle('Saving Video')
    progressDialog.setAutoClose(False)
    progressDialog.setAutoReset(False)
    progressDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    progressDialog.setMinimumDuration(500)

    if specialFormat:
        _runLegacy(self.videoToTroubleshootSplitVideo, filename, progressDialog, firstFrame, lastFrame)
    else:
      numerator, denominator = map(float, subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-of", "default=noprint_wrappers=1:nokey=1", "-show_entries", "stream=r_frame_rate", self.videoToTroubleshootSplitVideo], universal_newlines=True).split('/'))
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
