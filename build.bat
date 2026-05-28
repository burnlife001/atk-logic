@echo off
setlocal
set "QT_DIR=D:\Programs\Qt\5.15.2\msvc2019_64"
set "PROJECT_DIR=E:\__electric\atk-logic"

call "D:\Programs\MSStudio\CommunityApp\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] vcvars64.bat failed
    exit /b 1
)

cd /d "%PROJECT_DIR%"

set BUILD=Release
if not "%1"=="" set BUILD=%1

echo ========================================
echo  Building ATK-Logic: %BUILD%
echo ========================================

:: Step 1: qmake
echo [1/3] qmake...
"%QT_DIR%\bin\qmake.exe" ATK-Logic.pro
if errorlevel 1 (
    echo [ERROR] qmake failed
    exit /b 1
)

:: Step 2: compile
echo [2/3] nmake...
nmake %BUILD%
if errorlevel 1 (
    echo [ERROR] nmake failed
    exit /b 1
)

:: Step 3: deploy dependencies
echo [3/3] Deploy runtime...
copy /y "%PROJECT_DIR%\lib\bin\*.dll" "%PROJECT_DIR%\%BUILD%\" >nul 2>&1
xcopy /s /e /y "%PROJECT_DIR%\lib\python3.14" "%PROJECT_DIR%\%BUILD%\lib\python3.14\" >nul 2>&1
"%QT_DIR%\bin\windeployqt.exe" "%PROJECT_DIR%\%BUILD%\ATK-Logic.exe" --qmldir "%PROJECT_DIR%\qml" --no-translations >nul 2>&1

echo.
echo ========================================
echo  Build OK: %BUILD%
echo  Output: %PROJECT_DIR%\%BUILD%\ATK-Logic.exe
echo ========================================
endlocal
