@echo off
setlocal enabledelayedexpansion

:: Set working directory to script location
cd /d "%~dp0"

:: === Create log file ===
set "logfile=log_%date:~-4%-%date:~3,2%-%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%.txt"
set "logfile=%logfile: =0%"  :: Remove spaces from filename
echo --- Starting session at %date% %time% --- > "%logfile%"

:: === Get and print current time ===
set "currentTime=%time%"
echo Current time: %currentTime%
echo Current time: %currentTime% >> "%logfile%"

:: === Extract and clean hour ===
for /f "tokens=1 delims=:" %%a in ("%currentTime%") do (
    set "hour=%%a"
)
if "!hour:~0,1!"=="0" set "hour=!hour:~1!"
set /a hour=!hour!
echo Parsed hour: !hour!
echo Parsed hour: !hour! >> "%logfile%"


:: Call logic
if !hour! GEQ 6 if !hour! LEQ 7 (
    echo Would call run_session2.bat
    call run_session2.bat
    goto wait
)


:: Call logic
if !hour! GEQ 10 if !hour! LEQ 12 (
    echo Would call run_session3.bat
    call run_session3.bat
    goto wait
)

:: Call logic
if !hour! GEQ 16 if !hour! LEQ 17 (
    echo Would call run_session3.bat
    call run_session4.bat
    goto wait
)
echo No matching time range. No session executed.
echo No matching time range. No session executed. >> "%logfile%"

:wait
echo Waiting 1 minute before exit...
echo Waiting 1 minute before exit... >> "%logfile%"
timeout /t 60 /nobreak > nul