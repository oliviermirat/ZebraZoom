import sys
import os
dir_path = os.path.dirname(os.path.realpath(__file__))
print("The data produced by ZebraZoom can be found in the folder: " + os.path.join(dir_path,'ZZoutput'))

from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()

if len(sys.argv) == 1:

  from zebrazoom.GUIAllPy import SampleApp
  if __name__ == "__main__":
    app = SampleApp()
    app.mainloop()
    
else:

  if sys.argv[1] == "getTailExtremityFirstFrame":
    
    pathToVideo = sys.argv[2]
    videoName   = sys.argv[3]
    videoExt    = sys.argv[4]
    configFile  = sys.argv[5]
    argv        = sys.argv
    argv.pop(0)
    from zebrazoom.getTailExtremityFirstFrame import getTailExtremityFirstFrame
    if __name__ == '__main__':
      __spec__ = "ModuleSpec(name='builtins', loader=<class '_frozen_importlib.BuiltinImporter'>)"
      getTailExtremityFirstFrame(pathToVideo, videoName, videoExt, configFile, argv)
      
  elif sys.argv[1] == "recreateSuperStruct":
    
    pathToVideo = sys.argv[2]
    videoName   = sys.argv[3]
    videoExt    = sys.argv[4]
    configFile  = sys.argv[5]
    argv        = sys.argv
    argv.pop(0)
    from zebrazoom.recreateSuperStruct import recreateSuperStruct
    if __name__ == '__main__':
      __spec__ = "ModuleSpec(name='builtins', loader=<class '_frozen_importlib.BuiltinImporter'>)"
      recreateSuperStruct(pathToVideo, videoName, videoExt, configFile, argv)
      
  elif sys.argv[1] == "convertSeqToAvi":
    
    from zebrazoom.videoFormatConversion.seq_to_avi import sqb_convert_to_avi
    path      = sys.argv[2]
    videoName = sys.argv[3]
    if len(sys.argv) == 5:
      lastFrame = int(sys.argv[4])
    else:
      lastFrame = -1
    sqb_convert_to_avi(path, videoName, lastFrame)

  else:
  
    pathToVideo = sys.argv[1]
    videoName   = sys.argv[2]
    videoExt    = sys.argv[3]
    configFile  = sys.argv[4]
    argv        = sys.argv
    from zebrazoom.mainZZ import mainZZ
    if __name__ == '__main__':
      __spec__ = "ModuleSpec(name='builtins', loader=<class '_frozen_importlib.BuiltinImporter'>)"
      mainZZ(pathToVideo, videoName, videoExt, configFile, argv)

