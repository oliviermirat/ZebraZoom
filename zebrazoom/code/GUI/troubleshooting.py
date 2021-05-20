import tkinter as tk
from tkinter import font  as tkfont
from tkinter import filedialog
from tkinter import ttk
from tkinter import *
from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()
import webbrowser

class ChooseVideoToTroubleshootSplitVideo(tk.Frame):

  def __init__(self, parent, controller):
    
    def callback(url):
      webbrowser.open_new(url)
    
    tk.Frame.__init__(self, parent)
    self.controller = controller
    
    label = tk.Label(self, text="Troubleshooting.", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    link2 = tk.Button(self, text="First View Tracking Troubleshooting Tips", bg="gold")
    link2.pack()
    link2.bind("<Button-1>", lambda e: callback("https://github.com/oliviermirat/ZebraZoom/blob/master/TrackingTroubleshooting.md"))
    tk.Label(self, text='').pack()
    
    label = tk.Label(self, text="If the previous tracking troubleshooting tips where not enough to solve the issue, you can create a smaller sub-video to send to ZebraZoom's developers for troubleshooting.")
    label.pack(side="top", fill="x", pady=10)
    
    tk.Button(self, text="Select the video to troubleshoot.", command=lambda: controller.chooseVideoToTroubleshootSplitVideo(controller)).pack()

    tk.Label(self, text="If you are having issues running the tracking on a video or creating a good configuration file for a video", font=("Helvetica", 10)).pack(side="top", fill="x")
    tk.Label(self, text="you can create a sub-video centered around a bout of movement and send this smaller sub-video to info@zebrazoom.org in order for us to help troubleshoot.", font=("Helvetica", 10)).pack(side="top", fill="x")
    tk.Label(self, text="Click on the button above to start this process.", font=("Helvetica", 10)).pack(side="top", fill="x")
    tk.Label(self, text="(if your video is light enough you can also send it to info@zebrazoom.org without reducing its size)", font=("Helvetica", 10)).pack(side="top", fill="x")
    tk.Label(self, text='').pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()

class VideoToTroubleshootSplitVideo(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    
    tk.Label(self, text="Ok, your sub-video has been saved in the folder you chose. You can now send that sub-video to info@zebrazoom.org", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()
    