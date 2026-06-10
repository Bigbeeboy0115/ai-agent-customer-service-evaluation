@echo off
setlocal
cd /d "%~dp0"

echo Starting AI Agent Customer Service Evaluation app...
echo Project: %CD%
echo.

if exist "I:\anaconda\python.exe" (
  set "PYTHON_CMD=I:\anaconda\python.exe"
  goto run_app
)

where conda >nul 2>nul
if %ERRORLEVEL%==0 (
  call conda activate base
  goto run_app
)

for %%D in (
  "I:\anaconda"
  "%USERPROFILE%\anaconda3"
  "%USERPROFILE%\miniconda3"
  "%LOCALAPPDATA%\anaconda3"
  "%LOCALAPPDATA%\miniconda3"
  "C:\ProgramData\anaconda3"
  "C:\ProgramData\miniconda3"
) do (
  if exist "%%~D\Scripts\activate.bat" (
    call "%%~D\Scripts\activate.bat" "%%~D"
    goto run_app
  )
)

where python >nul 2>nul
if %ERRORLEVEL%==0 goto run_app

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py --version >nul 2>nul
  if %ERRORLEVEL%==0 (
    set "PYTHON_CMD=py"
    goto run_app
  )
)

echo Could not find conda or python in this terminal.
echo Please open Anaconda Prompt once and run:
echo cd /d "%~dp0"
echo python -m streamlit run app.py
pause
exit /b 1

:run_app
if "%PYTHON_CMD%"=="" set "PYTHON_CMD=python"

"%PYTHON_CMD%" -m pip show streamlit >nul 2>nul
if not %ERRORLEVEL%==0 (
  echo Installing dependencies from requirements.txt...
  "%PYTHON_CMD%" -m pip install -r requirements.txt
)

echo.
echo Opening Streamlit at http://localhost:8501
"%PYTHON_CMD%" -m streamlit run app.py
pause
