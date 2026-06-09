@echo off
echo ===================================================
echo   ADAPTIVE COMPRESSION - PROFESSIONAL BUILD TOOL
echo ===================================================

echo [1/4] Installing dependencies...
python -m pip install pyinstaller customtkinter psutil Pillow zstandard lz4

echo [2/4] Cleaning old build data...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo [3/4] Running PyInstaller...
:: --onefile: bundle into single exe
:: --windowed: no console window
:: --add-data "bin;bin": include engine binaries
:: --add-data "data;data": include history database
:: --icon: set app icon
python -m PyInstaller --noconfirm --onefile --windowed --add-data "bin;bin" --add-data "data;data" --icon "app_icon.ico" app.py

echo [4/4] Verifying build...
if exist dist\app.exe (
    echo.
    echo SUCCESS! Your professional executable is ready in the 'dist' folder.
    explorer dist
) else (
    echo.
    echo ERROR: Build failed. Check the logs above.
)

pause