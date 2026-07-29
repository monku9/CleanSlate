@echo off
REM Builds a standalone CleanSlate.exe that people can double-click
REM without needing Python installed. Run this on Windows.
REM
REM NOTE: we call "python -m PyInstaller" instead of just "pyinstaller".
REM On some Python installs (like the Python Install Manager / per-user
REM installs), the pyinstaller.exe script isn't added to PATH even
REM though the package is installed. Calling it as a module through
REM "python -m" always works because it goes through python.exe directly.

echo Installing PyInstaller (only needed once)...
python -m pip install --upgrade pyinstaller

echo.
echo Building CleanSlate.exe ...
python -m PyInstaller --onefile --windowed --name "CleanSlate" app.py

echo.
echo Done! Find your app in the "dist" folder.
pause
