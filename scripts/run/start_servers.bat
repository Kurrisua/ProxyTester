@echo off
set "PROJECT_ROOT=%~dp0..\.."
pushd "%PROJECT_ROOT%"

REM Start API server
echo Starting API server...
start "API Server" python api.py

REM Wait for 3 seconds
echo Waiting 3 seconds...
timeout /t 3 /nobreak >nul

REM Start frontend server
echo Starting frontend server...
cd daili
start "Frontend Server" npm run dev
cd ..

REM Show completion message
echo Servers started successfully!
echo API server: http://localhost:5000
echo Frontend: http://localhost:3000

REM Pause to view output
echo Press any key to exit...
pause
popd
