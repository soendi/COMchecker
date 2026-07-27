; Inno Setup Installer Script for COMchecker
; Requires Inno Setup 6+ for Unicode support

#define MyAppName "COMchecker"
#define MyAppVersion "1.0.0.7"
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
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=admin
OutputDir=dist\
OutputBaseFilename=COMchecker-Setup
SetupIconFile=resources\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
DisableProgramGroupPage=yes
AppMutex=COMcheckerAppMutex
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktopsymbol erstellen"; GroupDescription: "Zusätzliche Symbole:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "resources\icon.ico"; DestDir: "{app}\resources"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Lukas Sonderegger\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Lukas Sonderegger\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Lukas Sonderegger\{#MyAppName}"; ValueType: string; ValueName: "InstallDate"; ValueData: "{code:GetDateString}"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  KeepSettings: Boolean;

function GetDateString(Param: string): string;
begin
  Result := GetDateTimeString('dd.mm.yyyy', '-', ':');
end;

function InitializeUninstall: Boolean;
begin
  Result := True;
  KeepSettings := MsgBox(
    'Sollen Ihre Einstellungen (Registry) erhalten bleiben?' #13#13
    'Ja  â€“ Einstellungen, Datenbank und Logdateien bleiben erhalten' #13
    'Nein â€“ Alles wird gelÃ¶scht inklusive Datenbank und Logdateien',
    mbConfirmation, MB_YESNO) = IDYES;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if not KeepSettings then
    begin
      RegDeleteKeyIncludingSubkeys(HKCU, 'Software\Lukas Sonderegger\COMchecker');
      DelTree(ExpandConstant('{localappdata}\COMchecker'), True, True, True);
      DelTree(ExpandConstant('{userappdata}\COMchecker'), True, True, True);
    end;
  end;
end;
