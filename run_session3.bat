@echo off
echo Running Claude Automation - Sessions 7 to 12
cd /d "%~dp0"

for %%i in (18 19 20 21) do (
    echo Running Session %%i...
    python -m src.simple_sender --session session%%i --run-one
    echo Session %%i completed

    echo.
    echo Waiting 1 minute before next session...
    timeout /t 60 /nobreak >nul

    echo ==============================================
    echo.
)

echo All sessions completed successfully
