$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (!(Get-Command vagrant -ErrorAction SilentlyContinue)) { throw 'Install Vagrant and VirtualBox first. See README.md.' }
vagrant up --provider=virtualbox
if ($LASTEXITCODE -ne 0) { throw 'Vagrant startup failed. Check the error above.' }
Write-Host 'Open http://127.0.0.1:8080 after creating an account. See README.md.'
