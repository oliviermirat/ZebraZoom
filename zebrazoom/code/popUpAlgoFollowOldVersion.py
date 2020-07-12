import tkinter as tk
from tkinter import Tk, mainloop, TOP
from threading import Timer

from vars import getGlobalVariables
globalVariables = getGlobalVariables()

def initialise():
  if globalVariables["mac"] != 1:
    f = open("trace.txt","w+")
    f.write("")
    f.close() 
    def launchStuff():
      root = Tk()
      label2 = tk.Text(root)
      label2.pack()
      def changeLabelValue():
        f = open("trace.txt", "r")
        if f.mode == 'r':
          contents = f.read()
        f.close()
        label2.delete('1.0', tk.END)
        label2.insert(tk.END, contents)
        if "ZebraZoom Analysis all finished" in contents:
          # if closePopUpWindowAtTheEnd:
          root.destroy()
        else:
          r = Timer(1.0, changeLabelValue, ())
          r.start()          
      r = Timer(1.0, changeLabelValue, ())
      r.start()
      root.mainloop()
    
    f = Timer(0.5, launchStuff, ())
    f.start()

def prepend(text):
  if globalVariables["mac"] != 1:
    with open("trace.txt", "r+") as f:
      content = f.read()
      f.seek(0, 0)
      f.write(text.rstrip('\r\n') + '\n' + content)
