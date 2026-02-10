@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "PY="

if defined VIRTUAL_ENV (
  if exist "%VIRTUAL_ENV%\Scripts\python.exe" (
    set "PY=%VIRTUAL_ENV%\Scripts\python.exe"
  )
)

if not defined PY (
  if exist "C:\Scripts\.venv2\Scripts\python.exe" (
    set "PY=C:\Scripts\.venv2\Scripts\python.exe"
  )
)

if not defined PY (
  if exist "%ROOT%.venv2\Scripts\python.exe" (
    set "PY=%ROOT%.venv2\Scripts\python.exe"
  )
)

if not defined PY (
  if exist "%ROOT%.venv\Scripts\python.exe" (
    set "PY=%ROOT%.venv\Scripts\python.exe"
  )
)

if not defined PY (
  where py >nul 2>&1
  if %errorlevel%==0 (
    set "PY=py -3.11"
  ) else (
    set "PY=python"
  )
)

echo [INFO] Python: %PY%
echo [INFO] Starting Flask app at http://127.0.0.1:5000
echo.

%PY% app.py

echo.
pause
endlocal
