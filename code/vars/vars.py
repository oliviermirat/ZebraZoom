import platform

def getGlobalVariables():
  var = {}
  
  # When var["mac"] == 1, no specification of file extension in the GUI during prompt + Patience page before tracking launch + sets spawn as initialization method for multiprocessing + no pop-up to follow progress during tracking + closes GUI after config file creation
  var["mac"] = int(platform.system() == "Darwin")
  
  # When var["lin"] == 1, Patience page before tracking launch + closes GUI after config file creation
  var["lin"] = int(platform.system() == "Linux")
  
  # Checking that the OS can be detected
  if ((int(platform.system() == "Darwin") + int(platform.system() == "Linux") + int(platform.system() == "Windows")) != 1):
    print("Problem detecting OS used!")
  
  # When var["noMultiprocessing"] = 1, no multiprocessing of wells
  var["noMultiprocessing"] = 0
  
  return var