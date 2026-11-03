@echo off
title Run Tests & Evals - Hoardings
cd /d "%~dp0"

echo ===================================================
echo   Running Tests & Quality Evaluation Suite...
echo ===================================================

set PYTHONPATH=backend
set DEEPEVAL_TELEMETRY_OPT_OUT=YES

python -m pytest backend/tests/ backend/evals/ -v -p no:deepeval

echo.
echo ===================================================
echo   Test Execution Complete!
echo ===================================================
pause

