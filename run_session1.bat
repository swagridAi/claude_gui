@echo off
echo Running Claude Automation - Research Questions Session
cd /d "%~dp0"
python -m src.simple_sender --session session1
echo Session completed
pause