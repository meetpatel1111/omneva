; Omneva Media Player Installer Script
; Generated for Inno Setup

#define MyAppName "Omneva"
#define MyAppVersion "1.4.1"
#define MyAppPublisher "Meetkumar Patel"
#define MyAppURL "https://github.com/meetpatel1111/omneva"
#define MyAppExeName "Omneva.exe"
#define MyAppDescription "A powerful, feature-rich media player with transcoding capabilities"
#define MyAppAuthor "pmeet464@gmail.com"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{8B5A3F2A-1C4D-4E7F-9A2B-3D6E8F1C4A9D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright={#MyAppPublisher} © 2026
AppComments={#MyAppDescription}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE.txt
InfoBeforeFile=README.md
OutputDir=installer_output
OutputBaseFilename=Omneva-Setup-{#MyAppVersion}
SetupIconFile=src\assets\icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
ShowTasksTreeLines=yes
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
CreateAppDir=yes
DisableDirPage=no
DisableProgramGroupPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Create a Quick Launch icon"; GroupDescription: "Additional icons:"; Flags: unchecked; OnlyBelowVersion: 0,6.1
Name: "fileassoc"; Description: "Associate media files with {#MyAppName}"; GroupDescription: "File associations:"; Flags: unchecked
Name: "ctxmenu"; Description: "Add to Windows context menu"; GroupDescription: "Integration:"; Flags: unchecked
Name: "startup"; Description: "Launch {#MyAppName} on startup"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
; Install main executable (onefile mode)
Source: "dist\Omneva.exe"; DestDir: "{app}"; Flags: ignoreversion
; Install documentation
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "Launch {#MyAppName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"; Comment: "Remove {#MyAppName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "Launch {#MyAppName}"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon; Comment: "Launch {#MyAppName}"
Name: "{group}\{cm:ProgramOnTheWeb,{#MyAppName}}"; Filename: "{#MyAppURL}"; Comment: "Visit {#MyAppName} website"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Registry]
; Register file associations for media files (conditional on task)
Root: HKCR; Subkey: ".mp3"; ValueType: string; ValueName: ""; ValueData: "Omneva.MediaFile"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".mp4"; ValueType: string; ValueName: ""; ValueData: "Omneva.MediaFile"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".avi"; ValueType: string; ValueName: ""; ValueData: "Omneva.MediaFile"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".mkv"; ValueType: string; ValueName: ""; ValueData: "Omneva.MediaFile"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".mov"; ValueType: string; ValueName: ""; ValueData: "Omneva.MediaFile"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".wmv"; ValueType: string; ValueName: ""; ValueData: "Omneva.MediaFile"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".flv"; ValueType: string; ValueName: ""; ValueData: "Omneva.MediaFile"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".webm"; ValueType: string; ValueName: ""; ValueData: "Omneva.MediaFile"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".m4a"; ValueType: string; ValueName: ""; ValueData: "Omneva.MediaFile"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".wav"; ValueType: string; ValueName: ""; ValueData: "Omneva.MediaFile"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".ogg"; ValueType: string; ValueName: ""; ValueData: "Omneva.MediaFile"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".flac"; ValueType: string; ValueName: ""; ValueData: "Omneva.MediaFile"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".aac"; ValueType: string; ValueName: ""; ValueData: "Omneva.MediaFile"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".3gp"; ValueType: string; ValueName: ""; ValueData: "Omneva.MediaFile"; Flags: uninsdeletevalue; Tasks: fileassoc

; Media file type registration
Root: HKCR; Subkey: "Omneva.MediaFile"; ValueType: string; ValueName: ""; ValueData: "Media File"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "Omneva.MediaFile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: "Omneva.MediaFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: "Omneva.MediaFile\shell\play"; ValueType: string; ValueName: ""; ValueData: "Play with {#MyAppName}"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: "Omneva.MediaFile\shell\play\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletevalue; Tasks: fileassoc

; Context menu integration (conditional on task)
Root: HKCR; Subkey: "Directory\Background\shell\Omneva"; ValueType: string; ValueName: ""; ValueData: "Open with {#MyAppName}"; Flags: uninsdeletevalue; Tasks: ctxmenu
Root: HKCR; Subkey: "Directory\Background\shell\Omneva\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%V"""; Flags: uninsdeletevalue; Tasks: ctxmenu
Root: HKCR; Subkey: "Directory\shell\Omneva"; ValueType: string; ValueName: ""; ValueData: "Open with {#MyAppName}"; Flags: uninsdeletevalue; Tasks: ctxmenu
Root: HKCR; Subkey: "Directory\shell\Omneva\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletevalue; Tasks: ctxmenu

; Startup registry entry (conditional on task)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startup

; Application registration
Root: HKLM; Subkey: "Software\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletevalue

[Code]
procedure InitializeWizard;
begin
  // Customize welcome page
  WizardForm.WelcomeLabel1.Caption := 'Welcome to the {#MyAppName} Setup Wizard';
  WizardForm.WelcomeLabel2.Caption := 'This will install {#MyAppName} version {#MyAppVersion} on your computer.' + #13#10 + #13#10 + '{#MyAppDescription}';
  
  // Customize finished page
  WizardForm.FinishedLabel.Caption := '{#MyAppName} has been successfully installed on your computer.' + #13#10 + #13#10 + 'Click Finish to close the setup wizard.';
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  // Skip the ready page for cleaner installation
  Result := (PageID = wpReady);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  
  // Check if VLC is installed (optional but recommended)
  if CurPageID = wpSelectDir then
  begin
    // Check for VLC installation
    if not RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\VideoLAN\VLC') then
    begin
      if MsgBox('VLC Media Player was not detected on your system.' + #13#10 + #13#10 +
                 'VLC is required for media playback in {#MyAppName}.' + #13#10 +
                 'Would you like to continue anyway and install VLC later?', 
                 mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
      end;
    end;
  end;
end;

procedure CurInstallChanged(CurPage: Integer);
begin
  // Update progress text
  case CurPage of
    wpInstalling:
      WizardForm.StatusLabel.Caption := 'Installing {#MyAppName} files...';
    wpFinished:
      WizardForm.StatusLabel.Caption := '{#MyAppName} installation completed successfully!';
  end;
end;

procedure DeinitializeUninstall();
begin
  // Clean up any remaining registry entries or files
  // This is called when the uninstaller finishes
end;
