[Setup]
AppId={{05E40DED-CE0A-437E-B90C-25A32B47880F}
AppName=MicroK8s for Windows
AppVersion=1.0.0
;AppVerName=MicroK8s for Windows 1.0.0
AppPublisher=Canonical Ltd.
AppPublisherURL=https://microk8s.io/
AppSupportURL=https://microk8s.io/
AppUpdatesURL=https://microk8s.io/
DefaultDirName={autopf}\MicroK8s for Windows
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE
MinVersion=10
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
SetupIconFile=microk8s.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
OutputBaseFilename=microk8s-installer
OutputDir=..\dist
ChangesEnvironment=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: modifypath; Description: "Add MicroK8s to the current user's PATH (Recommended)"

[Files]
Source: "..\dist\microk8s.exe"; DestDir: "{app}"; Flags: ignoreversion

[Code]
const
  ModPathName = 'modifypath';
  ModPathType = 'user';

function InitializeSetup(): Boolean;
var
  Version: TWindowsVersion;
  S: String;
begin
  GetWindowsVersionEx(Version);

  // Disallow installation on Home edition of Windows
  if Version.SuiteMask and VER_SUITE_PERSONAL <> 0 then
  begin
    SuppressibleMsgBox('MicroK8s cannot be installed on Home edition of Windows 10.',
      mbCriticalError, MB_OK, IDOK);
    Result := False;
    Exit;
  end;
  Result := True;
end;

function ModPathDir(): TArrayOfString;
begin
  SetArrayLength(Result, 1);
  Result[0] := ExpandConstant('{app}');
end;
#include "modpath.iss"

procedure CurStepChanged(CurStep: TSetupStep);
var
  Success: Boolean;
begin
  Success := True;
  if CurStep = ssPostInstall then
  begin
    if WizardIsTaskSelected(ModPathName) then
      ModPath();
  end;
end;

[Run]
Filename: "{app}\microk8s.exe"; Parameters: "install --assume-yes"; StatusMsg: "Setting up MicroK8s for the first time"; Description: "Setup and start MicroK8s?"; Flags: postinstall runascurrentuser

[UninstallRun]
Filename: "{app}\microk8s.exe"; Parameters: "uninstall"