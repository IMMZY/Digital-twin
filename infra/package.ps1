Write-Host "Packaging Lambda function..."

Set-Location ..\backend

# Install Linux-compatible binaries for Lambda's x86_64 runtime
pip install -r requirements.txt -t .\package `
  --platform manylinux2014_x86_64 `
  --only-binary=:all: `
  --python-version 3.12 `
  --quiet

Copy-Item *.py package\
if (Test-Path data) { Copy-Item -Recurse data package\data }

Compress-Archive -Path package\* -DestinationPath ..\infra\lambda.zip -Force

Remove-Item -Recurse -Force package

Write-Host "Done: infra\lambda.zip created"
