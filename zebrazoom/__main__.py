import sys
sys.path.insert(1, './')
sys.path.insert(1, './code/')
sys.path.insert(1, './code/GUI/')
sys.path.insert(1, './code/getImage/')
sys.path.insert(1, './code/vars/')
sys.path.insert(1, './code/tracking/')
sys.path.insert(1, './code/tracking/headTrackingHeadingCalculation/')
sys.path.insert(1, './code/tracking/tailTracking/')
sys.path.insert(1, './code/tracking/tailTracking/tailTrackingExtremityDetect/')
sys.path.insert(1, './code/tracking/tailTracking/tailTrackingExtremityDetect/findTailExtremete/')

from vars import getGlobalVariables
globalVariables = getGlobalVariables()

from GUIAllPy import SampleApp

if __name__ == "__main__":
  app = SampleApp()
  app.mainloop()
