@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "INPUT=%~1"
if "%INPUT%"=="" set "INPUT=%ROOT%inputs"

set "OUTPUT=%ROOT%outputs"
set "STEMS=4"
set "SCRIPT=%ROOT%src\music_splitter.py"

if not exist "%SCRIPT%" (
  echo [ERROR] Script not found: "%SCRIPT%"
  goto :end
)

set "PY="

if defined VIRTUAL_ENV (
  if exist "%VIRTUAL_ENV%\Scripts\python.exe" (
    set "PY=%VIRTUAL_ENV%\Scripts\python.exe"
  )
)

if not defined PY (
  if exist "%ROOT%.venv\Scripts\python.exe" (
    set "PY=%ROOT%.venv\Scripts\python.exe"
  )
)

if not defined PY (
  if exist "%ROOT%.venv2\Scripts\python.exe" (
    set "PY=%ROOT%.venv2\Scripts\python.exe"
  )
)

if not defined PY (
  if exist "C:\Scripts\.venv2\Scripts\python.exe" (
    set "PY=C:\Scripts\.venv2\Scripts\python.exe"
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

echo [INFO] Input : "%INPUT%"
echo [INFO] Output: "%OUTPUT%"
echo [INFO] Stems : %STEMS%
echo [INFO] Python: %PY%
echo.

%PY% "%SCRIPT%" "%INPUT%" --stems %STEMS% --output "%OUTPUT%"
if not %errorlevel%==0 (
  echo.
  echo [ERROR] Separation failed.
  echo [HINT] Spleeter'in kurulu oldugu venv ile calistirin.
  echo [HINT] Ornek:
  echo [HINT]   C:\Scripts\.venv2\Scripts\activate
  echo [HINT]   C:\Scripts\Music\run_splitter.bat
  goto :end
)

echo.
echo [OK] Completed successfully.

:end
echo.
pause
endlocal
