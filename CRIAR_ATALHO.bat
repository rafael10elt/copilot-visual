@echo off
title Criando Atalho do Lumi Copilot...
color 0A

echo ==========================================
echo   LUMI COPILOT - CRIADOR DE ATALHO
echo ==========================================
echo.

set SCRIPT="%TEMP%\%RANDOM%-%RANDOM%.vbs"

echo Set oWS = WScript.CreateObject("WScript.Shell") >> %SCRIPT%
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\Lumi Copilot AI.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "%~dp0backend\run_bot.bat" >> %SCRIPT%
echo oLink.WorkingDirectory = "%~dp0backend" >> %SCRIPT%
echo oLink.Description = "Inicializador do Motor de IA MT5" >> %SCRIPT%
echo oLink.IconLocation = "cmd.exe, 0" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%

cscript /nologo %SCRIPT%
del %SCRIPT%

echo [SUCESSO] Atalho 'Lumi Copilot AI' criado na sua Area de Trabalho!
echo.
pause