# ATK-Logic Proxy DLL Build Script (MSVC x64)
param(
    [ValidateSet('Release', 'Debug')]
    [string]$Build = 'Release'
)

$ErrorActionPreference = 'Stop'

$VSBat   = 'D:\Programs\MSStudio\CommunityApp\VC\Auxiliary\Build\vcvars64.bat'
$ProjDir = "$PSScriptRoot"

$DebugFlags = if ($Build -eq 'Debug') { '/Zi /D_DEBUG' } else { '' }
$Optimize  = if ($Build -eq 'Debug') { '/Od' } else { '/O2' }
$LinkDebug = if ($Build -eq 'Debug') { '/DEBUG' } else { '' }

function Run-VSCmd {
    param([string]$Cmd)
    $fullCmd = "`"$VSBat`" >nul 2>&1 && $Cmd"
    cmd /c $fullCmd
    if ($LASTEXITCODE -ne 0) { throw "Command failed: $Cmd" }
}

Write-Host '========================================' -ForegroundColor Cyan
Write-Host "  Building Proxy DLL: $Build"             -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan

$clFlags = "/nologo /LD $Optimize /MD /GS- $DebugFlags"
$linkFlags = "/DEF:Qt5Network_proxy.def $LinkDebug"

$cmd = @"
cd /d `"$ProjDir`" && cl $clFlags proxy_main.c /Fe:Qt5Network.dll /link $linkFlags kernel32.lib user32.lib ws2_32.lib
"@

Write-Host "[1/1] Compiling proxy_main.c -> Qt5Network.dll..."
Run-VSCmd $cmd

Write-Host ''
Write-Host '========================================' -ForegroundColor Green
Write-Host "  Build OK: Qt5Network.dll"             -ForegroundColor Green

$dll = Get-Item "$ProjDir\Qt5Network.dll"
Write-Host "  Size: $([math]::Round($dll.Length / 1024, 1)) KB" -ForegroundColor Green
Write-Host '========================================' -ForegroundColor Green
