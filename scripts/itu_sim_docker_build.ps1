param(
  [string]$RepoRoot = "$PSScriptRoot\..\..\auv-software"
)

Write-Host "Building ITU AUV Docker images..." -ForegroundColor Cyan
docker build -f "$RepoRoot\docker\Dockerfile.auv-base" -t itu-auv-base "$RepoRoot"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker build -f "$RepoRoot\docker\Dockerfile.auv" -t itu-auv "$RepoRoot"
exit $LASTEXITCODE

