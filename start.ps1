$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.\.venv\Scripts\python.exe')) {
    throw 'Python-Umgebung fehlt. Installation siehe docs/windows_vscode.md.'
}
& .\.venv\Scripts\python.exe scripts/prepare_database.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& .\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
exit $LASTEXITCODE
