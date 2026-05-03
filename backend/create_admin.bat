@echo off
setlocal
cd /d "%~dp0"

if "%AFN_BOOTSTRAP_ADMIN_PASSWORD%"=="" (
  echo Set AFN_BOOTSTRAP_ADMIN_PASSWORD before running this script.
  exit /b 1
)

py create_admin.py
endlocal
