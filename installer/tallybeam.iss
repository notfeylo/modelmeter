#ifndef AppVersion
  #define AppVersion "0.4.0"
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

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\src-tauri\target\release\Tallybeam.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\TallybeamBackend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\build\MicrosoftEdgeWebView2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Tallybeam"; Filename: "{app}\Tallybeam.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Tallybeam"; Filename: "{app}\Tallybeam.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{tmp}\MicrosoftEdgeWebView2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Installing Microsoft WebView2 Runtime..."; Check: WebView2Missing
Filename: "{app}\Tallybeam.exe"; Description: "Launch Tallybeam"; Flags: nowait postinstall skipifsilent

[Code]
function WebView2Missing(): Boolean;
var
  Version: String;
  Key: String;
begin
  Key := 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  Result := True;
  if RegQueryStringValue(HKCU, Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0') then
    Result := False;
  if RegQueryStringValue(HKLM, 'Software\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0') then
    Result := False;
end;
