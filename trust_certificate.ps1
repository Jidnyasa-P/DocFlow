# DocFlow — trust the local certificate (run this ONCE per computer)
#
# Office Add-ins require HTTPS, even for a purely local server. DocFlow
# generates its own certificate on first run (server/certs.py) instead of
# requiring Node.js/npx -- this script just tells Windows and your browser
# to trust that certificate. No admin rights needed: it installs into the
# CURRENT USER's trusted root store, not the machine-wide one.
#
# Usage: right-click this file -> "Run with PowerShell"
#   (or, from a terminal: powershell -ExecutionPolicy Bypass -File trust_certificate.ps1)

$certPath = Join-Path $env:APPDATA "DocFlow\certs\localhost.crt"

if (-not (Test-Path $certPath)) {
    Write-Host "No certificate found at $certPath" -ForegroundColor Red
    Write-Host "Run DocFlow.exe (or 'python server/app.py') at least once first --"
    Write-Host "it generates the certificate automatically on first start."
    exit 1
}

Write-Host "Found certificate at $certPath"
Write-Host "Installing into your user's Trusted Root Certification Authorities..."

Import-Certificate -FilePath $certPath -CertStoreLocation Cert:\CurrentUser\Root

Write-Host ""
Write-Host "Done. Restart your browser (and Word, if it's open) for this to take effect." -ForegroundColor Green
Write-Host "You should no longer see certificate warnings for https://localhost:3000"
