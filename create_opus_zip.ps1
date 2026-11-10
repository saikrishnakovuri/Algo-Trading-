$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root

$target = Join-Path $root 'opus_review'
if (Test-Path $target) { Remove-Item -Path $target -Recurse -Force }
New-Item -ItemType Directory -Path $target | Out-Null

$files = @(
    'backtest_engine.py',
    'orchestrator.py',
    'master_optimizer.py',
    'main_backtest.py',
    'run_backtest.py',
    'optimized_gemini_client.py',
    'debug_gemini_api.py',
    'live_trader_v1.py',
    'live_trader_v2.py',
    'live_trader_v3.py',
    'live_options_trader.py',
    'live_dry_run.py',
    'live_trader_crypto.py',
    'meta_config.json',
    'meta_db.json',
    'requirements.txt',
    'OPUS_AGENT_REVIEW.md'
)

foreach ($f in $files) {
    if (Test-Path $f) {
        Copy-Item -Path $f -Destination $target -Force
    } else {
        Write-Host "MISSING_FILE: $f"
    }
}

$dirs = @('config','utils','tests','scripts')
foreach ($d in $dirs) {
    if (Test-Path $d) {
        Copy-Item -Path $d -Destination $target -Recurse -Force
    } else {
        Write-Host "MISSING_DIR: $d"
    }
}

# Create zip archive (exclude sensitive files by not copying them)
$zipName = Join-Path $root 'opus review.zip'
if (Test-Path $zipName) { Remove-Item -Path $zipName -Force }
Compress-Archive -Path (Join-Path $target '*') -DestinationPath $zipName -Force
Write-Host "ZIP_CREATED: $zipName"

# cleanup
Remove-Item -Path $target -Recurse -Force
Write-Host "CLEANED_UP"
