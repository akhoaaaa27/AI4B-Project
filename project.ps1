param(
    [ValidateSet('setup', 'dev', 'backend', 'frontend', 'check', 'smoke', 'ui')]
    [string]$Action = 'dev'
)

$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$projectRoot = Join-Path $PSScriptRoot 'GreenSegment-AI-feature-greensegment-v2'
$projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    $projectPython = (Get-Command python -ErrorAction Stop).Source
}
& $projectPython (Join-Path $projectRoot 'tools\project.py') $Action
exit $LASTEXITCODE
