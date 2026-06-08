@echo off
chcp 65001 >nul
title QAAssistant
echo ================================================
echo        Medical QA Assistant
echo ================================================
echo.

:: 切换到 bat 所在目录，避免路径问题
cd /d "%~dp0"

:: 直接在当前窗口运行 exe（可以看到错误信息）
"QAAssistant.exe"

:: 如果 exe 退出，暂停显示错误
echo.
echo Service has stopped.
pause
