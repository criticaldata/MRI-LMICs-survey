<#
.SYNOPSIS
Regenerates and verifies the reviewer-corrected MRI-LMICs analysis package.

.DESCRIPTION
Runs only local scripts and cached evidence. It does not publish data or modify
GitHub. Final Fleiss' kappa is calculated only when a private reviewer workbook
is supplied; the workbook itself is never copied into the public repository.
#>

[CmdletBinding()]
param(
    [string]$PythonPath,
    [string]$RunDate = (Get-Date -Format "yyyyMMdd"),
    [string]$PrivateRatingsXlsx
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path

if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $PythonPath = Join-Path $repoRoot ".venv-reproducible\\Scripts\\python.exe"
}

if (-not (Test-Path -LiteralPath $PythonPath)) {
    & powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "bootstrap_reproducible_env.ps1")
}

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Python runtime was not created: $PythonPath"
}

function Invoke-MriPython {
    param(
        [Parameter(Mandatory = $true)][string]$Script,
        [string[]]$Arguments = @()
    )

    # Arguments may contain the private workbook path; never echo them.
    Write-Host "Running: $Script"
    & $PythonPath $Script @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Failed: $Script"
    }
}

Push-Location $repoRoot
try {
    Invoke-MriPython "scripts/analysis/run_reproducible_review_analysis.py" @("--promote", "--run-date", $RunDate)
    Invoke-MriPython "scripts/analysis/run_tr_weighting_sensitivity.py"
    Invoke-MriPython "scripts/analysis/extract_metric_ground_truth_from_cached_fulltext.py"
    Invoke-MriPython "scripts/analysis/statistical/run_random_forest_robustness_20260804.py"
    Invoke-MriPython "scripts/tables/analysis_temporal_trends.py"
    Invoke-MriPython "scripts/figures/fig4_performance_comparison.py"
    Invoke-MriPython "scripts/figures/figS1_temporal_trends.py"

    if ([string]::IsNullOrWhiteSpace($PrivateRatingsXlsx)) {
        Write-Host "Skipping private reviewer analyses: no private reviewer workbook supplied."
    }
    else {
        if (-not (Test-Path -LiteralPath $PrivateRatingsXlsx)) {
            throw "Private reviewer workbook not found: $PrivateRatingsXlsx"
        }
        Invoke-MriPython "scripts/analysis/statistical/run_fleiss_kappa_from_private_xlsx.py" @(
            "--input-xlsx", $PrivateRatingsXlsx,
            "--output-dir", "tables",
            "--canonical-data", "data/data-clean.csv"
        )
        Invoke-MriPython "scripts/analysis/statistical/run_weighted_kappa_from_private_xlsx.py" @(
            "--input-xlsx", $PrivateRatingsXlsx,
            "--output-dir", "tables",
            "--canonical-data", "data/data-clean.csv"
        )
        Invoke-MriPython "scripts/analysis/statistical/run_icc_from_private_xlsx.py" @(
            "--input-xlsx", $PrivateRatingsXlsx,
            "--output-dir", "tables",
            "--canonical-data", "data/data-clean.csv"
        )
        Invoke-MriPython "scripts/analysis/statistical/run_lmic_tr_correlation_from_private_xlsx.py" @(
            "--input-xlsx", $PrivateRatingsXlsx,
            "--output-dir", "tables",
            "--canonical-data", "data/data-clean.csv"
        )
    }

    Invoke-MriPython "scripts/analysis/build_public_reproducibility_package.py"
    Invoke-MriPython "scripts/analysis/verify_reproducibility.py"
    Invoke-MriPython "scripts/analysis/verify_mri_scientometric_reproducibility.py" @("--public-release")

    Write-Host "Running: -m pytest -q"
    & $PythonPath -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw "Failed: pytest"
    }
}
finally {
    Pop-Location
}

Write-Host "Complete. All reviewer-corrected local outputs were regenerated and verified."
