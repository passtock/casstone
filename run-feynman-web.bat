@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PATH=%LOCALAPPDATA%\Programs\feynman\bin;%PATH%"
set "NODE_OPTIONS=--max-old-space-size=12288"
echo [Feynman Web] 현재 프로젝트 폴더에서 웹 UI를 실행합니다 (메모리 12GB 확장 및 메모리 누수 방지 적용): %CD%
feynman serve
pause
