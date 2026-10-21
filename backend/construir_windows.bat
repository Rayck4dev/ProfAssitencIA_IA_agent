@echo off
rem ProfAssistenc - gera o programa (.exe) e o pacote .zip para Windows.
rem Basta dar dois cliques neste arquivo. Requer Python 3.11 ou mais novo.
setlocal
cd /d "%~dp0"
echo ============================================================
echo  ProfAssistenc - gerar o programa (.exe) para Windows
echo ============================================================
echo.

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo Python nao encontrado.
  echo Instale o Python 3.11 ou mais novo em https://www.python.org/downloads/
  echo e marque a opcao "Add python.exe to PATH" no instalador.
  goto :erro
)

if not exist ".venv-build\Scripts\python.exe" (
  echo Criando o ambiente de build ^(so na primeira vez^)...
  %PY% -m venv .venv-build || goto :erro
)
call ".venv-build\Scripts\activate.bat" || goto :erro
python -m pip install --upgrade pip --quiet
echo Instalando as dependencias...
python -m pip install -r requirements-build.txt || goto :erro
echo.
python build_exe.py %* || goto :erro

echo.
echo ============================================================
echo  Pronto! O pacote para distribuir esta na pasta "dist".
echo  Para criar tambem o instalador, abra installer\ProfAssistenc.iss
echo  no Inno Setup. Veja docs\DISTRIBUICAO.md.
echo ============================================================
pause
exit /b 0

:erro
echo.
echo Algo deu errado. Leia as mensagens acima.
pause
exit /b 1
