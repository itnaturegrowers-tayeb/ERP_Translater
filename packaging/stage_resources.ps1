param(
    [string]$TesseractRoot = "C:\Program Files\Tesseract-OCR",
    [string]$ModelRoot = "$env:USERPROFILE\.local\share\argos-translate\packages"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Resources = Join-Path $PSScriptRoot "resources"
$ResolvedPackaging = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$ExpectedResources = Join-Path $ResolvedPackaging "resources"

if ($Resources -ne $ExpectedResources) {
    throw "Refusing to stage resources outside the packaging directory."
}
if (Test-Path -LiteralPath $Resources) {
    Remove-Item -LiteralPath $Resources -Recurse -Force
}
New-Item -ItemType Directory -Path $Resources | Out-Null

# Stage the portable Tesseract engine. Only Spanish OCR data is required.
if (-not (Test-Path -LiteralPath (Join-Path $TesseractRoot "tesseract.exe"))) {
    throw "Tesseract was not found at $TesseractRoot"
}
$TesseractDestination = Join-Path $Resources "tesseract"
New-Item -ItemType Directory -Path $TesseractDestination | Out-Null
Get-ChildItem -LiteralPath $TesseractRoot -File | Where-Object {
    $_.Name -eq "tesseract.exe" -or
    $_.Extension -eq ".dll" -or
    $_.Name -match "^(LICENSE|COPYING|NOTICE|README)"
} | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $TesseractDestination
}
$TessdataDestination = Join-Path $TesseractDestination "tessdata"
New-Item -ItemType Directory -Path $TessdataDestination | Out-Null
$SpanishDataCandidates = @(
    (Join-Path $ProjectRoot ".runtime\tessdata\spa.traineddata"),
    (Join-Path $TesseractRoot "tessdata\spa.traineddata")
)
$SpanishData = $SpanishDataCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $SpanishData) {
    throw "Spanish Tesseract data (spa.traineddata) was not found."
}
Copy-Item -LiteralPath $SpanishData -Destination $TessdataDestination

# Stage only translation model/tokenizer files. Stanza assets are intentionally excluded.
$ModelsDestination = Join-Path $Resources "models"
New-Item -ItemType Directory -Path $ModelsDestination | Out-Null
$RequiredPairs = @("es_en", "en_es", "en_fr", "en_ar")
$FoundPairs = @{}
Get-ChildItem -LiteralPath $ModelRoot -Filter metadata.json -Recurse -File | ForEach-Object {
    $Metadata = Get-Content -LiteralPath $_.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    $Pair = "$($Metadata.from_code)_$($Metadata.to_code)"
    if ($RequiredPairs -contains $Pair -and -not $FoundPairs.ContainsKey($Pair)) {
        $Source = $_.Directory.FullName
        $Destination = Join-Path $ModelsDestination $Pair
        New-Item -ItemType Directory -Path $Destination | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $Destination
        $ModelReadme = Join-Path $Source "README.md"
        if (Test-Path -LiteralPath $ModelReadme) {
            Copy-Item -LiteralPath $ModelReadme -Destination $Destination
        }
        foreach ($TokenizerName in @("sentencepiece.model", "bpe.model")) {
            $Tokenizer = Join-Path $Source $TokenizerName
            if (Test-Path -LiteralPath $Tokenizer) {
                Copy-Item -LiteralPath $Tokenizer -Destination $Destination
            }
        }
        Copy-Item -LiteralPath (Join-Path $Source "model") -Destination $Destination -Recurse
        $FoundPairs[$Pair] = $true
    }
}

$MissingPairs = $RequiredPairs | Where-Object { -not $FoundPairs.ContainsKey($_) }
if ($MissingPairs) {
    throw "Missing translation models: $($MissingPairs -join ', ')"
}

$Size = (Get-ChildItem -LiteralPath $Resources -Recurse -File | Measure-Object Length -Sum).Sum
Write-Output ("Resources staged: {0:N1} MB" -f ($Size / 1MB))
