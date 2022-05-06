;--------------------------------
;Include Modern UI and StrFunc

  !include "MUI2.nsh"
  !include "StrFunc.nsh"
  ${UnStrTrimNewLines}

;--------------------------------
;General

  ;Name and file
  Name "ZebraZoom"
  OutFile "ZebraZoom.exe"
  Unicode True

  ;Default installation folder
  InstallDir "$PROGRAMFILES64\ZebraZoom"

  ;Get installation folder from registry if available
  InstallDirRegKey HKCU "Software\ZebraZoom" ""

  ;Request application privileges
  RequestExecutionLevel user

;--------------------------------
;Variables

  Var StartMenuFolder

;--------------------------------
;Interface Settings

  !define MUI_ABORTWARNING

;--------------------------------
;Pages

  !insertmacro MUI_PAGE_DIRECTORY

  ;Start Menu Folder Page Configuration
  !define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKCU"
  !define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\ZebraZoom"
  !define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "Start Menu Folder"

  !insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder

  !insertmacro MUI_PAGE_INSTFILES

  ;Ask the user if he wants a desktop shortcut
  Function finishpageaction
  CreateShortcut "$DESKTOP\ZebraZoom.lnk" "$INSTDIR\ZebraZoom.exe"
  FunctionEnd

  !define MUI_FINISHPAGE_SHOWREADME ""
  !define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
  !define MUI_FINISHPAGE_SHOWREADME_TEXT "Create desktop shortcut"
  !define MUI_FINISHPAGE_SHOWREADME_FUNCTION finishpageaction
  !insertmacro MUI_PAGE_FINISH

  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES

  !insertmacro MUI_LANGUAGE "English"

;--------------------------------
;Installer Sections

Section "Install" "Install ZebraZoom."

  SetOutPath "$INSTDIR"

  File /r "build\dist\ZebraZoom\*"

  ;Store installation folder
  WriteRegStr HKCU "Software\ZebraZoom" "" $INSTDIR

  ;Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application

    ;Create shortcuts
    CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
    CreateShortcut "$SMPROGRAMS\$StartMenuFolder\ZebraZoom.lnk" "$INSTDIR\ZebraZoom.exe"
    CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk" "$INSTDIR\Uninstall.exe"

  !insertmacro MUI_STARTMENU_WRITE_END

SectionEnd

;--------------------------------
;Uninstaller Section

Section "Uninstall" "Uninstall ZebraZoom."


  Delete "$INSTDIR\Uninstall.exe"

  FileOpen $0 $INSTDIR\installedFiles.txt r
  LOOP:
  FileRead $0 $1
  IfErrors exit_loop
  ${UnStrTrimNewLines} $1 $1
  StrCmp $1 "installedFiles.txt" LOOP 0
  IfFileExists "$INSTDIR\$1\*.*" 0 +2
    RMDir "$INSTDIR\$1"
  IfFileExists "$INSTDIR\$1" 0 LOOP
    Delete "$INSTDIR\$1"
  ClearErrors
  Goto LOOP
  exit_loop:
  FileClose $0
  Delete "$INSTDIR\installedFiles.txt"
  RMDir "$INSTDIR"

  !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder

  Delete "$DESKTOP\ZebraZoom.lnk"

  Delete "$SMPROGRAMS\$StartMenuFolder\ZebraZoom.lnk"
  Delete "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk"
  RMDir "$SMPROGRAMS\$StartMenuFolder"

  DeleteRegKey /ifempty HKCU "Software\ZebraZoom"

SectionEnd
