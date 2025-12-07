@echo off
REM Configure Depot Addresses
REM Quick helper to update depot addresses in .env file

echo ======================================================================
echo DT Logistics - Depot Configuration Helper
echo ======================================================================
echo.
echo This script helps you configure depot addresses for each state.
echo Current depots will be shown, and you can update them if needed.
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause >nul
echo.

REM Check if .env exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo Please ensure you are in the project root directory.
    pause
    exit /b 1
)

echo Current Depot Configuration:
echo ============================================================
echo.

REM Display current depots
findstr /B "DEPOT_" .env

echo.
echo ============================================================
echo.
echo To update depot addresses:
echo 1. Open .env file in a text editor
echo 2. Find the DEPOT_NSW, DEPOT_VIC, etc. lines
echo 3. Update with your actual warehouse addresses
echo 4. Save the file
echo.
echo Example format:
echo DEPOT_NSW="Your NSW warehouse full address with state and postcode"
echo.
echo Would you like to:
echo   1. Open .env in Notepad for editing
echo   2. Test current depot configuration
echo   3. Exit
echo.
choice /C 123 /N /M "Enter choice (1, 2, or 3): "

if errorlevel 3 goto :end
if errorlevel 2 goto :test
if errorlevel 1 goto :edit

:edit
echo.
echo Opening .env in Notepad...
notepad .env
echo.
echo File saved! Would you like to test the configuration?
choice /C YN /N /M "Test depot configuration? (Y/N): "
if errorlevel 2 goto :end
if errorlevel 1 goto :test

:test
echo.
echo Testing depot configuration...
echo.
python test_depot_manager.py
echo.
echo Test complete!
goto :end

:end
echo.
echo ======================================================================
echo Configuration complete!
echo ======================================================================
echo.
echo Next steps:
echo   1. Run: python generate_demo_manifests.py
echo   2. Run: python app.py
echo   3. View driver manifests to see optimal depot selection
echo.
pause
