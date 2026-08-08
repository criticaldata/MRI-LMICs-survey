<#
.SYNOPSIS
Creates the isolated local environment used by the corrected MRI review.

.DESCRIPTION
The script never uses API credentials and does not write to GitHub. It refuses
to overwrite an existing environment, so a rerun is safe. Remove the selected
environment directory manually only when intentionally rebuilding it.
#>

[CmdletBinding()]
param(
    [string]$PythonLauncher = "py",
    [string]$EnvironmentPath = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\..")) ".venv-reproducible")
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$requirements = Join-Path $repoRoot "requirements-reproducible-review.txt"

if (Test-Path -LiteralPath $EnvironmentPath) {
    throw "Environment already exists: $EnvironmentPath. It was not modified."
}

if (-not (Test-Path -LiteralPath $requirements)) {
    throw "Missing requirements file: $requirements"
}

& $PythonLauncher -3.12 -m venv $EnvironmentPath
$python = Join-Path $EnvironmentPath "Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r $requirements
& $python -m pip check

Write-Host "Environment ready: $EnvironmentPath"
Write-Host "Run: & '$python' -m pytest -q"
