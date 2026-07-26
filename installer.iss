; Inno Setup Installer Script for COMchecker
; Based on KOFplanner installer pattern

#define MyAppName "COMchecker"
#define MyAppVersion "1.0.0.0"
#define MyAppPublisher "Lukas Sonderegger"
#define MyAppURL "https://github.com/soendi/COMchecker"
#define MyAppExeName "COMchecker.exe"

[Setup]
AppId={{A3F8B7D2-5E9C-4B1A-7D6F-3C2E5A8B9D0E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={userpf}\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputDir=.
OutputBaseFilename={#MyAppName}-Setup
SetupIconFile=resources\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
DisableProgramGroupPage=yes
AppMutex=COMcheckerAppMutex
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktopsymbol erstellen"; GroupDescription: "Zus&auml;tzliche Symbole:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "resources\icon.ico"; DestDir: "{app}\resources"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Lukas Sonderegger\{#MyAppName}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Lukas Sonderegger\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Lukas Sonderegger\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Lukas Sonderegger\{#MyAppName}"; ValueType: string; ValueName: "InstallDate"; ValueData: "{code:GetDateString}"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
function GetDateString(Param: string): string;
begin
  Result := GetDateTimeString('dd.mm.yyyy', '-', ':');
end;
