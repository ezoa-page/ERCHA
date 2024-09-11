@echo off
echo Cleaning up...
python setup.py clean --all
if %ERRORLEVEL% neq 0 (
    echo [Error] Cleaning failed. Exiting...
    exit /b %ERRORLEVEL%
)
echo Building extension...
python setup.py build_ext --inplace
if %ERRORLEVEL% neq 0 (
    echo [Error] Building extension failed. Exiting...
    exit /b %ERRORLEVEL%
)
echo Building exe...
pyinstaller --onefile --clean --name ercha --icon=assets/ercha.ico --hidden-import ercha.cli --hidden-import ercha.rch --hidden-import ercha.lzw --hidden-import ercha.config --hidden-import ercha.logger ercha_launcher.py
if %ERRORLEVEL% neq 0 (
    echo [Error] Building exe failed. Exiting...
    exit /b %ERRORLEVEL%
)
echo Building installer...
wix build installer.wxs -arch x64 -out ERCHA.msi
if %ERRORLEVEL% neq 0 (
    echo [Error] Creating installer failed. Exiting...
    exit /b %ERRORLEVEL%
)
echo Generating WinGet Manifest...
python generate_winget_manifest.py
if %ERRORLEVEL% neq 0 (
    echo [Error] Creating WinGet manifest failed. Exiting...
    exit /b %ERRORLEVEL%
)