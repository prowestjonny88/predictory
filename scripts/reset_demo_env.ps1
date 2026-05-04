param(
    [switch]$IncludeNodeModules
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$paths = @(
    "predictory.db",
    "apps/api/predictory.db",
    "apps/web/.next",
    "apps/web/tsconfig.tsbuildinfo",
    ".pytest_cache",
    "apps/api/.pytest_cache"
)

foreach ($path in $paths) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
        Write-Host "Removed $path"
    }
}

Get-ChildItem -Path . -Directory -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Where-Object {
        $_.FullName -notlike "*\backend\models\*" -and
        $_.FullName -notlike "*\apps\web\public\demo-data\*"
    } |
    Remove-Item -Recurse -Force

if ($IncludeNodeModules) {
    foreach ($path in @("apps/web/node_modules", "node_modules")) {
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Recurse -Force
            Write-Host "Removed $path"
        }
    }
}

Write-Host "Demo environment reset complete. Accepted ML artifacts and frontend demo data were preserved."
