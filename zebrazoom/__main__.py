import os
dir_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(dir_path)
print("The data produced by ZebraZoom can be found in the folder: " + os.path.join(dir_path,'ZZoutput'))

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

from GUIAllPy import SampleApp

if __name__ == "__main__":
  app = SampleApp()
  app.mainloop()
