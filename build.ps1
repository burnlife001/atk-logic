param(
    [ValidateSet('Debug', 'Release')]
    [string]$Build = 'Release'
)

$ErrorActionPreference = 'Stop'

$VSBat    = 'D:\Programs\MSStudio\CommunityApp\VC\Auxiliary\Build\vcvars64.bat'
$QtDir    = 'D:\Programs\Qt\5.15.2\msvc2019_64'
$ProjDir  = 'E:\__electric\atk-logic'
$OutDir   = "$ProjDir\$Build"

function Run-VSCmd {
    param([string]$Cmd)
    $fullCmd = "`"$VSBat`" >nul 2>&1 && $Cmd"
    cmd /c $fullCmd
    if ($LASTEXITCODE -ne 0) { throw "Command failed:`n  $Cmd" }
}

Write-Host '========================================' -ForegroundColor Cyan
Write-Host "  Building ATK-Logic: $Build"             -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
Write-Host ''

# Step 1: qmake
Write-Host '[1/3] qmake...' -ForegroundColor Yellow
Run-VSCmd "cd /d `"$ProjDir`" && `"$QtDir\bin\qmake.exe`" ATK-Logic.pro"

# Step 2: nmake
Write-Host '[2/3] nmake...' -ForegroundColor Yellow
Run-VSCmd "cd /d `"$ProjDir`" && nmake $Build"

# Step 3: deploy
Write-Host '[3/3] Deploy runtime...' -ForegroundColor Yellow
Copy-Item "$ProjDir\lib\bin\*.dll" $OutDir -Force -ErrorAction SilentlyContinue
if (Test-Path "$ProjDir\lib\python3.14") {
    Copy-Item "$ProjDir\lib\python3.14" "$OutDir\lib\python3.14" -Recurse -Force
}
Run-VSCmd "`"$QtDir\bin\windeployqt.exe`" `"$OutDir\ATK-Logic.exe`" --qmldir `"$ProjDir\qml`" --no-translations"

Write-Host ''
Write-Host '========================================' -ForegroundColor Green
Write-Host "  Build OK: $Build"                     -ForegroundColor Green
Write-Host "  Output:  $OutDir\ATK-Logic.exe"        -ForegroundColor Green
Write-Host '========================================' -ForegroundColor Green
