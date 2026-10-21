; Instalador do ProfAssistenc (Inno Setup 6.3 ou mais novo, gratuito: jrsoftware.org)
;
; Como usar:
;   1) Gere o programa:  backend\construir_windows.bat
;   2) Abra este arquivo no Inno Setup e clique em Build > Compile.
;   3) O instalador sai em installer\output\ProfAssistenc-Setup-<versao>.exe
;
; O instalador NAO inclui a chave nem as conversas: cada professor informa a sua chave
; na primeira abertura, e atualizar por cima nao apaga o historico.

#define MyAppName "ProfAssistenc"
#define MyAppVersion "2.1.0"
#define MyAppExe "ProfAssistenc.exe"
#define BuildDir "..\backend\dist\ProfAssistenc"

[Setup]
AppId={{8F3C2B1E-6D54-4A7B-9C0E-2A1B7D5E4F63}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=ProfAssistenc
; Instala na pasta do usuario: nao precisa de senha de administrador e o programa
; pode gravar o banco e a chave ao lado do executavel.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=ProfAssistenc-Setup-{#MyAppVersion}
SetupIconFile=..\assets\favicon.ico
UninstallDisplayIcon={app}\{#MyAppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na Área de Trabalho"; GroupDescription: "Atalhos:"; Flags: checkedonce

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LEIA-ME.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Abrir o ProfAssistenc agora"; Flags: nowait postinstall skipifsilent

[Code]
// Ao desinstalar, pergunta se as conversas e a chave devem ser apagadas.
// Por padrao elas ficam, para o professor nao perder o historico.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if DirExists(ExpandConstant('{app}')) then
    begin
      if MsgBox('Deseja apagar também as conversas e a chave salvas neste computador?' + #13#10 +
                'Escolha "Não" para guardá-las (recomendado se for reinstalar).',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(ExpandConstant('{app}'), True, True, True);
    end;
  end;
end;
