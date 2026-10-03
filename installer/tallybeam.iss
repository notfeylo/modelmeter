#ifndef AppVersion
  #define AppVersion "0.7.0"
#endif

[Setup]
AppId={{66F20A87-4833-43EE-A505-3CF116BAEA40}
AppName=Modelmeter
AppVersion={#AppVersion}
AppVerName=Modelmeter {#AppVersion}
AppPublisher=notfeylo
AppPublisherURL=https://github.com/notfeylo/modelmeter
AppSupportURL=https://github.com/notfeylo/modelmeter/issues
AppUpdatesURL=https://github.com/notfeylo/modelmeter/releases
DefaultDirName={localappdata}\Programs\Modelmeter
DefaultGroupName=Modelmeter
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=Modelmeter-Setup-{#AppVersion}-win-x64
SetupIconFile=..\assets\tallybeam.ico
UninstallDisplayIcon={app}\Modelmeter.exe
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
Type: files; Name: "{app}\Tallybeam.exe"
Type: files; Name: "{autoprograms}\Tallybeam.lnk"
Type: files; Name: "{autodesktop}\Tallybeam.lnk"

[Files]
Source: "..\src-tauri\target\release\Modelmeter.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\TallybeamBackend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist\ModelmeterStatusline\*"; DestDir: "{app}\statusline"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\build\MicrosoftEdgeWebView2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Modelmeter"; Filename: "{app}\Modelmeter.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Modelmeter"; Filename: "{app}\Modelmeter.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{tmp}\MicrosoftEdgeWebView2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Installing Microsoft WebView2 Runtime..."; Check: WebView2Missing
Filename: "{app}\Modelmeter.exe"; Description: "Launch Modelmeter"; Flags: nowait postinstall skipifsilent

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
