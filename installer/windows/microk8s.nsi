!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "LogicLib.nsh"
!include "Sections.nsh"

!define PRODUCT_NAME "MicroK8s"
!define PRODUCT_VERSION "2.3.3"
!define PRODUCT_PUBLISHER "Canonical"
!define MUI_ICON ".\microk8s.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP ".\microk8s.bmp"
!define MUI_HEADERIMAGE_RIGHT

Unicode True
Name "${PRODUCT_NAME} for Windows ${PRODUCT_VERSION}"
BrandingText "Canonical Ltd."
Icon ".\microk8s.ico"
OutFile "microk8s-installer.exe"
InstallDir "$PROGRAMFILES64\${PRODUCT_NAME}"
ShowInstDetails hide
RequestExecutionLevel admin
SetCompress auto

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\..\LICENSE"
!define MUI_COMPONENTSPAGE_TEXT_COMPLIST " "
!define MUI_COMPONENTSPAGE_TEXT_INSTTYPE " "
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
Page custom ConfigureVm LaunchVm
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Var MultipassExitCode
Var VmConfigureDialog
Var VmConfigureDialogCpu
Var VmConfigureDialogCpuLabel
Var VmConfigureDialogMem
Var VmConfigureDialogMemLabel
Var VmConfigureDialogDisk
Var VmConfigureDialogDiskLabel
Var VmConfigureDialogTrack
Var VmConfigureDialogTrackLabel
Var VmConfigureDialogFootnote

Section "Multipass (Required)" multipass_id
;Exit 0 : Multipass is installed and backing hypervisor is ready to roll (e.g. HyperV is already enabled).
;Exit 3010: Multipass is installed but backing hypervisor requires a reboot (e.g. HyperV just enabled).
;Exit 3011: Multipass is installed but no backing hypervisor has been (e.g. virtualbox needs installing).
    SectionIn RO
    IfFileExists $PROGRAMFILES64\Multipass\bin\multipass.exe endMultipass beginMultipass
    Goto endMultipass
    beginMultipass:
        SetOutPath $INSTDIR
        File "multipass.exe"
        ${If} ${Silent}
            ExecWait "multipass.exe /NoRestart /S" $0
        ${Else}
            ExecWait "multipass.exe /NoRestart"  $0
        ${EndIf}
        StrCpy $MultipassExitCode $0
        IfErrors failedMultipass
        Delete "$INSTDIR\multipass.exe"
        Goto endMultipass
    failedMultipass:
        Abort
    endMultipass:
SectionEnd

Section "Kubectl (Required)" kubectl_id
    SectionIn RO
    beginKubectl:
        SetOutPath $INSTDIR
        File "kubectl.exe"
        CopyFiles "$INSTDIR\kubectl.exe" "$INSTDIR\kubectl\kubectl.exe"
        Delete "$INSTDIR\kubectl.exe"
        Goto endKubectl
    endKubectl:
SectionEnd

Section -Install
    SectionIn RO
    SetOutPath $INSTDIR
    File "microk8s.exe"
SectionEnd

Section -WriteUninstaller
    SectionIn RO
    WriteUninstaller $INSTDIR\uninstall.exe
    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "DisplayName" "${PRODUCT_NAME} ${PRODUCT_VERSION}"
    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "UninstallString" "$INSTDIR\uninstall.exe"
SectionEnd

Section "Add 'microk8s' to PATH" add_to_path_id
    EnVar::AddValue "path" "$INSTDIR"
SectionEnd

Section /o "Add 'kubectl' to PATH" add_kubectl_to_path_id
    EnVar::AddValue "path" "$INSTDIR\kubectl"
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${multipass_id} "REQUIRED: If already installed, will be unticked and skipped.$\n$\nSee https://multipass.run for more."
    !insertmacro MUI_DESCRIPTION_TEXT ${add_to_path_id} "Add the 'microk8s' executable to PATH.$\n$\nThis will allow you to run the command 'microk8s' in cmd and PowerShell in any directory."
    !insertmacro MUI_DESCRIPTION_TEXT ${add_kubectl_to_path_id} "Add the 'kubectl' executable to PATH.$\n$\nThis will set the bundled 'kubectl' as system default."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Function .onInit
    DeleteRegKey HKLM "Software\canonical\multipass"
    IfFileExists $PROGRAMFILES64\Multipass\bin\multipass.exe untickMultipass tickMultipass
    tickMultipass:
        IntOp $0 ${SF_SELECTED} | ${SF_RO}
        SectionSetFlags ${multipass_id} $0
        Return
    untickMultipass:
        StrCpy $MultipassExitCode "0"  ; Multipass is installed.
        SectionSetFlags ${multipass_id} ${SF_RO}
        Return
FunctionEnd

Function "ConfigureVm"
    ${IfNot} $MultipassExitCode == "0"
        ${If} $MultipassExitCode == "3010"
            MessageBox MB_ICONEXCLAMATION "Cannot configure the ${PRODUCT_NAME} VM as a reboot is required.  Please re-run this wizard after reboot to configure the VM."
            SetRebootFlag true
            Abort
        ${ElseIf} $MultipassExitCode == "3011"
            MessageBox MB_ICONEXCLAMATION "Cannot configure the ${PRODUCT_NAME} VM as VirtualBox needs to be installed.  Please re-run this wizard after installing VirtualBox to configure the VM."
            Abort
        ${EndIf}
    ${EndIf}
    MessageBox MB_YESNO "Do you want to configure and launch the ${PRODUCT_NAME} VM now?" /SD IDYES IDNO endLaunch
        nsDialogs::Create 1018
        Pop $VmConfigureDialog

        ${NSD_CreateLabel} 19% 0 35u 10u "CPUs"
        Pop $VmConfigureDialogCpuLabel

        ${NSD_CreateLabel} 44% 0 35u 10u "Mem (GB)"
        Pop $VmConfigureDialogMemLabel

        ${NSD_CreateLabel} 69% 0 35u 10u "Disk (GB)"
        Pop $VmConfigureDialogDiskLabel

        ${NSD_CreateNumber} 19% 17.5 35u 10u "2"
        Pop $VmConfigureDialogCpu

        ${NSD_CreateNumber} 44% 17.5 35u 10u "4"
        Pop $VmConfigureDialogMem

        ${NSD_CreateNumber} 69% 17.5 35u 10u "50"
        Pop $VmConfigureDialogDisk

        ${NSD_CreateLabel} 42% 50 50u 10u "Snap Track"
        Pop $VmConfigureDialogTrackLabel

        ${NSD_CreateText} 42% 67.5 50u 10u "1.28/stable"
        Pop $VmConfigureDialogTrack

        ${NSD_CreateLabel} 8% 102.5 100% 10u "These are the minimum recommended parameters for the VM running ${PRODUCT_NAME}"
        Pop $VmConfigureDialogFootnote

        nsDialogs::Show
    endLaunch:
        Abort
FunctionEnd

Function "LaunchVM"
    ${NSD_GetText} $VmConfigureDialogCpu $0
    ${NSD_GetText} $VmConfigureDialogMem $1
    ${NSD_GetText} $VmConfigureDialogDisk $2
    ${NSD_GetText} $VmConfigureDialogTrack $3

    ExecWait "$INSTDIR\microk8s.exe install --cpu $0 --mem $1 --disk $2 --channel $3 --assume-yes"
FunctionEnd

Function un.onInit
    DeleteRegKey HKLM "Software\canonical\multipass"
FunctionEnd

Section "Uninstall"
    ExecWait "$INSTDIR\microk8s.exe uninstall"
    Delete $INSTDIR\uninstall.exe
    Delete $INSTDIR\microk8s.exe
    Delete $INSTDIR\kubectl\kubectl.exe
    RMDir $INSTDIR\kubectl
    RMDir $INSTDIR

    DeleteRegKey HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"

    EnVar::DeleteValue "path" "$INSTDIR"
    EnVar::DeleteValue "path" "$INSTDIR\kubectl"
SectionEnd
