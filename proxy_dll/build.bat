@echo off
setlocal
:: ATK-Logic Proxy DLL Build Script (MSVC x64)
:: Usage: build.bat

set MSVC_BASE=%ProgramFiles%\MSStudio\CommunityApp\VC\Tools\MSVC\14.51.36231
set MSVC_CL=%MSVC_BASE%\bin\Hostx64\x64\cl.exe
set MSVC_LINK=%MSVC_BASE%\bin\Hostx64\x64\link.exe

set SDK_BASE=%ProgramFiles(x86)%\Windows Kits\10
set SDK_INC=%SDK_BASE%\Include\10.0.26100.0
set SDK_LIB=%SDK_BASE%\Lib\10.0.26100.0

:: Find actual SDK version if 10.0.26100.0 doesn't exist
if not exist "%SDK_INC%" (
    for /f "delims=" %%d in ('dir /b /on "%SDK_BASE%\Include\10.*" 2^>nul') do set SDK_INC=%SDK_BASE%\Include\%%d
)
if not exist "%SDK_LIB%" (
    for /f "delims=" %%d in ('dir /b /on "%SDK_BASE%\Lib\10.*" 2^>nul') do set SDK_LIB=%SDK_BASE%\Lib\%%d
)

set INCLUDE=%MSVC_BASE%\include;%SDK_INC%\ucrt;%SDK_INC%\um;%SDK_INC%\shared
set LIB=%MSVC_BASE%\lib\x64;%SDK_LIB%\ucrt\x64;%SDK_LIB%\um\x64

echo Building proxy DLL...
echo INCLUDE=%INCLUDE%
echo LIB=%LIB%

"%MSVC_CL%" /nologo /LD /O2 /MT /GS- /Gs9999999 ^
    proxy_main.c ^
    /Fe:Qt5Network.dll ^
    /DEF:Qt5Network_proxy.def ^
    /link /NODEFAULTLIB /ENTRY:DllMain ^
    kernel32.lib user32.lib ws2_32.lib msvcrt.lib

if %ERRORLEVEL% neq 0 (
    echo BUILD FAILED
    exit /b 1
)

echo.
echo SUCCESS: Qt5Network.dll built
dir Qt5Network.dll 2>nul
endlocal
