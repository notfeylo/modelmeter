#ifndef AppVersion
  #define AppVersion "0.2.0"
#endif

[Setup]
AppId={{66F20A87-4833-43EE-A505-3CF116BAEA40}
AppName=Tallybeam
AppVersion={#AppVersion}
AppVerName=Tallybeam {#AppVersion}
AppPublisher=notfeylo
AppPublisherURL=https://github.com/notfeylo/tallybeam
AppSupportURL=https://github.com/notfeylo/tallybeam/issues
AppUpdatesURL=https://github.com/notfeylo/tallybeam/releases
DefaultDirName={localappdata}\Programs\Tallybeam
DefaultGroupName=Tallybeam
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=Tallybeam-Setup-{#AppVersion}-win-x64
SetupIconFile=..\assets\tallybeam.ico
UninstallDisplayIcon={app}\Tallybeam.exe
LicenseFile=..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: checkedonce

[Files]
Source: "..\dist\Tallybeam\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Tallybeam"; Filename: "{app}\Tallybeam.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Tallybeam"; Filename: "{app}\Tallybeam.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Tallybeam.exe"; Description: "Launch Tallybeam"; Flags: nowait postinstall skipifsilent
