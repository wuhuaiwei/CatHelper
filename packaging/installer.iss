#ifndef AppVersion
  #define AppVersion "1.2.1"
#endif

[Setup]
AppId={{5242B89F-DBB6-4E84-8306-40C5B2587247}
AppName=桌面猫助手
AppVersion={#AppVersion}
AppPublisher=CatAssistant
DefaultDirName={localappdata}\Programs\CatAssistant
DefaultGroupName=桌面猫助手
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
SourceDir=..
OutputDir=dist
OutputBaseFilename=CatAssistant-Setup-{#AppVersion}-x64
SetupIconFile=assets\cat.ico
UninstallDisplayIcon={app}\CatAssistant.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=yes
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "chinesesimp"; MessagesFile: "{#SourcePath}ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："
Name: "contextmenu"; Description: "添加资源管理器右键菜单（文件、文件夹和目录空白处）"; GroupDescription: "集成："

[Files]
Source: "dist\CatAssistant\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\召唤小猫"; Filename: "{app}\CatAssistant.exe"; Parameters: "--target ""{userdocs}"""; WorkingDir: "{userdocs}"
Name: "{group}\小猫设置"; Filename: "{app}\CatAssistant.exe"; Parameters: "--settings"; WorkingDir: "{userdocs}"
Name: "{group}\卸载桌面猫助手"; Filename: "{uninstallexe}"
Name: "{autodesktop}\桌面猫助手"; Filename: "{app}\CatAssistant.exe"; Parameters: "--target ""{userdocs}"""; WorkingDir: "{userdocs}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\*\shell\AIHelp"; ValueType: string; ValueName: ""; ValueData: "召唤小爱"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\AIHelp"; ValueType: string; ValueName: "MUIVerb"; ValueData: "召唤小爱"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\AIHelp"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\assets\cat.ico"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\AIHelp"; ValueType: string; ValueName: "Position"; ValueData: "Top"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\AIHelp"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Single"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\AIHelp\command"; ValueType: string; ValueName: ""; ValueData: """{app}\CatAssistant.exe"" --target ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\shell\AIHelp"; ValueType: string; ValueName: ""; ValueData: "召唤小爱"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\shell\AIHelp"; ValueType: string; ValueName: "MUIVerb"; ValueData: "召唤小爱"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\shell\AIHelp"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\assets\cat.ico"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\shell\AIHelp"; ValueType: string; ValueName: "Position"; ValueData: "Top"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\shell\AIHelp"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Single"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\shell\AIHelp\command"; ValueType: string; ValueName: ""; ValueData: """{app}\CatAssistant.exe"" --target ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\Background\shell\AIHelp"; ValueType: string; ValueName: ""; ValueData: "召唤小爱"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\Background\shell\AIHelp"; ValueType: string; ValueName: "MUIVerb"; ValueData: "召唤小爱"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\Background\shell\AIHelp"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\assets\cat.ico"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\Background\shell\AIHelp"; ValueType: string; ValueName: "Position"; ValueData: "Top"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\Background\shell\AIHelp\command"; ValueType: string; ValueName: ""; ValueData: """{app}\CatAssistant.exe"" --target ""%V"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\Background\shell\AIHelpSettings"; ValueType: string; ValueName: ""; ValueData: "小爱的设置…"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\Background\shell\AIHelpSettings"; ValueType: string; ValueName: "MUIVerb"; ValueData: "小爱的设置…"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\Background\shell\AIHelpSettings"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\assets\cat.ico"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\Background\shell\AIHelpSettings\command"; ValueType: string; ValueName: ""; ValueData: """{app}\CatAssistant.exe"" --settings"; Tasks: contextmenu

[Run]
Filename: "{app}\CatAssistant.exe"; Parameters: "--refresh-menu"; Flags: runhidden waituntilterminated; Tasks: contextmenu
Filename: "{app}\CatAssistant.exe"; Parameters: "--settings"; Description: "打开设置，选择已登录的 Codex / Claude CLI"; Flags: nowait postinstall skipifsilent
