import sys
sys.path.insert(1, './')
sys.path.insert(1, './code/')
sys.path.insert(1, './code/GUI/')
sys.path.insert(1, './code/getImage/')
sys.path.insert(1, './code/trackingFolder/')
sys.path.insert(1, './code/trackingFolder/headTrackingHeadingCalculationFolder/')
sys.path.insert(1, './code/trackingFolder/tailTrackingFunctionsFolder/')
sys.path.insert(1, './code/trackingFolder/tailTrackingFunctionsFolder/tailTrackingExtremityDetectFolder/')
sys.path.insert(1, './code/trackingFolder/tailTrackingFunctionsFolder/tailTrackingExtremityDetectFolder/findTailExtremeteFolder/')

from vars import getGlobalVariables
globalVariables = getGlobalVariables()

if len(sys.argv) == 1:

  from GUIAllPy import SampleApp
  if __name__ == "__main__":
    app = SampleApp()
    app.mainloop()

else:

  if len(sys.argv) >= 5:

    if sys.argv[1] == "getTailExtremityFirstFrame":
      
      pathToVideo = sys.argv[2]
      videoName   = sys.argv[3]
      videoExt    = sys.argv[4]
      configFile  = sys.argv[5]
      argv        = sys.argv
      argv.pop(0)
      from getTailExtremityFirstFrame import getTailExtremityFirstFrame
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
      from recreateSuperStruct import recreateSuperStruct
      if __name__ == '__main__':
        __spec__ = "ModuleSpec(name='builtins', loader=<class '_frozen_importlib.BuiltinImporter'>)"
        recreateSuperStruct(pathToVideo, videoName, videoExt, configFile, argv)
        
    else:
    
      pathToVideo = sys.argv[1]
      videoName   = sys.argv[2]
      videoExt    = sys.argv[3]
      configFile  = sys.argv[4]
      argv        = sys.argv
      from mainZZ import mainZZ
      if __name__ == '__main__':
        __spec__ = "ModuleSpec(name='builtins', loader=<class '_frozen_importlib.BuiltinImporter'>)"
        mainZZ(pathToVideo, videoName, videoExt, configFile, argv)
    