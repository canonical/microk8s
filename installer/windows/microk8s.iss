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
PrivilegesRequired=lowest
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