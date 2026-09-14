#define AppName "Harvest Opportunities"
#define AppVersion "1.0.0"
#define AppPublisher "Eastside Catholic School"
#define AppExeName "Harvest Opportunities.exe"

[Setup]
AppId={{D0379295-7989-4F30-B861-464E0C276083}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=C:\Users\AndrewKang\OneDrive - Eastside Catholic School\CMU Summer\Volunteer-Opportunity-Downloader\Volunteer-Opportunity-to-Padlet-Automation\Untitled\dist-holidays
OutputBaseFilename=Harvest Opportunities-Windows-Setup
SetupIconFile=C:\Users\AndrewKang\OneDrive - Eastside Catholic School\CMU Summer\Volunteer-Opportunity-Downloader\Volunteer-Opportunity-to-Padlet-Automation\Untitled\generated_assets\app-icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
ArchitecturesAllowed=x64compatible
MinVersion=10.0
VersionInfoVersion=1.0.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} installer
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "C:\Users\ANDREW~1\AppData\Local\Temp\harvest-checkbox-layout-20260914\Harvest Opportunities\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent



