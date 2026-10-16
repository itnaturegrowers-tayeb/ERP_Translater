param([switch]$SkipInstaller)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Project virtual environment not found."
}

& (Join-Path $PSScriptRoot "stage_resources.ps1")
& $Python -m PyInstaller --noconfirm --clean (Join-Path $PSScriptRoot "erp_translator.spec")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

# Copy Tesseract after PyInstaller analysis so its DLLs are not duplicated as binaries.
$DistInternal = Join-Path $ProjectRoot "dist\ERP Translator\_internal"
$TesseractSource = Join-Path $PSScriptRoot "resources\tesseract"
Copy-Item -LiteralPath $TesseractSource -Destination $DistInternal -Recurse

if (-not $SkipInstaller) {
    $CompilerCandidates = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
    )
    $Compiler = $CompilerCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $Compiler) {
        throw "Inno Setup 6 is not installed. Install it or use -SkipInstaller."
    }
    & $Compiler (Join-Path $PSScriptRoot "erp_translator.iss")
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup compilation failed."
    }
}

Write-Output "Packaging completed successfully."
