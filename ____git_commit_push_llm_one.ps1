# Auto Git Commit & Push
# Requires .env in the same directory with API_KEY (or MINIMAX_API_KEY), BASE_URL, LLM_MODEL

$ErrorActionPreference = "Stop"
$scriptDir = $PSScriptRoot
$envFile   = Join-Path $scriptDir ".env"

# ---------- load .env ----------
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*)\s*=\s*(.*?)\s*$') {
            $key   = $matches[1].Trim()
            $value = $matches[2].Trim() -replace "`r", ""
            if ($value -match '^["''](.*)["'']$') { $value = $matches[1] }
            Set-Item -Path "env:$key" -Value $value
        }
    }
}

# ---------- config ----------
$DEBUG_MODE = ($env:DEBUG_MODE -eq "true")
$BASE_URL   = if ($env:BASE_URL)   { $env:BASE_URL }   else { "https://api.minimaxi.com/v1" }
$LLM_MODEL  = if ($env:LLM_MODEL)  { $env:LLM_MODEL }  else { "MiniMax-M2.5" }
$apiKey     = if ($env:API_KEY)    { $env:API_KEY.Trim() } else { $env:MINIMAX_API_KEY.Trim() }

if (-not $apiKey) {
    Write-Host "Error: API key not configured." -ForegroundColor Red
    Write-Host "Set API_KEY or MINIMAX_API_KEY in .env or environment." -ForegroundColor Yellow
    Write-Host "`nPress any key to exit..." -ForegroundColor Cyan
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# ---------- ensure git on PATH ----------
$gitPaths = @("C:\Program Files\Git\cmd", "C:\Program Files (x86)\Git\cmd")
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    foreach ($p in $gitPaths) {
        if (Test-Path $p) { $env:PATH = "$p;$env:PATH"; break }
    }
}

# ---------- prompt template ----------
$LLM_PROMPT_TEMPLATE = @"
Generate a commit message for the Git diff below.

OUTPUT FORMAT (exactly follow this format):
Summary: One-sentence summary
    - [Add] filename
    - [Modify] filename: changes
    - [Delete] filename

IMPORTANT:
- Do NOT include any explanation, reasoning, or analysis
- Do NOT use thinking tags like <thinking>, （, （
- Do NOT include "Change content:" or diff details
- Output ONLY the commit message, nothing else
- Use present continuous tense

Git Diff:
{0}
"@

# ---------- helpers ----------
function Clear-GitProcesses {
    try {
        Write-Host "Checking for existing Git processes..." -ForegroundColor Cyan
        $procs = Get-Process -Name "git" -ErrorAction SilentlyContinue
        if ($procs -and $procs.Count -gt 0) {
            Write-Host "Found $($procs.Count) Git process(es), stopping..." -ForegroundColor Yellow
            $procs | Stop-Process -Force
            Start-Sleep -Seconds 2
        } else {
            Write-Host "No existing Git processes detected." -ForegroundColor Green
        }
        Write-Host "Checking for Git lock files..." -ForegroundColor Cyan
        $lockFiles = @()
        $indexLock = Join-Path ".git" "index.lock"
        if (Test-Path $indexLock) { $lockFiles += $indexLock }
        if (Test-Path ".git") {
            $lockFiles += Get-ChildItem -Path ".git" -Recurse -Filter "*.lock" | Select-Object -ExpandProperty FullName
        }
        if ($lockFiles.Count -gt 0) {
            Write-Host "Removing $($lockFiles.Count) lock file(s)..." -ForegroundColor Yellow
            foreach ($f in $lockFiles) {
                Remove-Item -Path $f -Force -ErrorAction SilentlyContinue
                Write-Host "  $f - $(if (Test-Path $f) { 'FAILED' } else { 'removed' })"
            }
        }
    } catch {
        Write-Host "Warning clearing Git state: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Get-GitChanges {
    $staged = git diff --staged --name-status 2>$null
    if (-not $staged) { return $null }
    $changes = @{ added = @(); modified = @(); deleted = @() }
    $staged | ForEach-Object {
        $status, $file = $_ -split "\s+", 2
        switch ($status) {
            "A" { $changes["added"]    += $file }
            "M" { $changes["modified"] += $file }
            "D" { $changes["deleted"]  += $file }
        }
    }
    return $changes
}

function Get-DetailedDiff {
    try {
        $diff = git diff --staged --patch 2>$null
        if (-not $diff) { return "No changes detected" }
        return [string]::Join("`n", $diff)
    } catch {
        return "Error getting diff content"
    }
}

function Get-LLMCommitMessage {
    param([Parameter(Mandatory)] [string]$diffContent)
    $prompt = $LLM_PROMPT_TEMPLATE -f $diffContent
    $maxRetries = 3
    for ($i = 0; $i -lt $maxRetries; $i++) {
        try {
            Write-Host "Calling $LLM_MODEL ..." -ForegroundColor Cyan
            $headers = @{ "Authorization" = "Bearer $apiKey"; "Content-Type" = "application/json" }
            $body = @{
                model       = $LLM_MODEL
                messages    = @(@{ role = "user"; content = $prompt })
                top_p       = 0.7
                temperature = 0.9
            } | ConvertTo-Json -Depth 5
            $response = Invoke-RestMethod -Uri "$BASE_URL/chat/completions" -Method Post -Headers $headers -Body $body -ContentType "application/json"
            if ($response -and $response.choices -and $response.choices.count -gt 0) {
                $msg = $response.choices[0].message.content
                $msg = $msg -replace '(?s)<thinking>.*?</thinking>', ''
                $msg = $msg -replace '(?s)<think>.*?</think>', ''
                $msg = $msg -replace '(?s)<analysis>.*?</analysis>', ''
                $msg = $msg -replace '(?s)<reasoning>.*?</reasoning>', ''
                $clean = $msg.Trim() -replace '(?m)^[ \t]+', ''
                $clean = $clean -replace '(?im)^commit message:\s*', ''
                if ($clean -match '(?m)^Summary:\s*(.*?)(\r?\n|$)') {
                    $summary = $matches[1].Trim()
                    $clean   = $clean -replace '(?m)^Summary:\s*.*?(\r?\n|$)', ''
                    $clean   = "Summary: $summary`r`n" + $clean.TrimStart()
                }
                $clean = $clean -replace '(?<!\r?\n)\s*-\s*\[', "`r`n- ["
                $clean = $clean -replace '(?m)^\s*$\r?\n', ''
                return $clean
            }
            throw "No valid response from LLM"
        } catch {
            if ($i -lt $maxRetries - 1) {
                Write-Host "Retry $($i+1)/${maxRetries}: $($_.Exception.Message)" -ForegroundColor Yellow
                Start-Sleep -Seconds (2 * ($i + 1))
            } else {
                Write-Host "LLM failed after ${maxRetries} retries: $($_.Exception.Message)" -ForegroundColor Red
                return $null
            }
        }
    }
    return $null
}

# ====================== main ======================
try {
    Clear-GitProcesses

    Write-Host "`nStaging all changes..." -ForegroundColor Cyan
    git add -A
    if ($LASTEXITCODE -ne 0) { throw "Failed to stage files" }
    Write-Host "Files staged." -ForegroundColor Green

    Write-Host "`nChecking staged changes..." -ForegroundColor Cyan
    $changes = Get-GitChanges
    if (-not $changes) {
        Write-Host "No changes to commit." -ForegroundColor Green
        Write-Host "`nPress any key to exit..." -ForegroundColor Cyan
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        exit 0
    }

    $diffContent = Get-DetailedDiff

    Write-Host "`nGenerating commit message via LLM..." -ForegroundColor Cyan
    $commitMessage = Get-LLMCommitMessage -diffContent $diffContent
    if (-not $commitMessage) {
        $currentDate   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $commitMessage = "LLM invalid, auto backup: $currentDate"
        Write-Host "Using fallback commit message." -ForegroundColor Yellow
    }

    Write-Host "`nCommit message:" -ForegroundColor Cyan
    Write-Host $commitMessage -ForegroundColor Green

    if ($DEBUG_MODE) {
        Write-Host "`n[Debug mode] Commit & push skipped." -ForegroundColor Yellow
    } else {
        Write-Host "`nCommitting..." -ForegroundColor Cyan
        $tmpFile = [System.IO.Path]::GetTempFileName()
        [System.IO.File]::WriteAllText($tmpFile, $commitMessage, [System.Text.UTF8Encoding]::new($false))
        git commit -F $tmpFile 2>&1 | Out-Null
        Remove-Item $tmpFile -Force
        Write-Host "Commit OK." -ForegroundColor Green

        Write-Host "`nPushing all branches..." -ForegroundColor Cyan
        git push --all origin 2>&1 | Out-Null
        Write-Host "Push OK." -ForegroundColor Green
    }

    Write-Host "`n=== Done ===" -ForegroundColor Green
} catch {
    Write-Host "`nError: $_" -ForegroundColor Red
} finally {
    Write-Host "`nPress any key to exit..." -ForegroundColor Cyan
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
