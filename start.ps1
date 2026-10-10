$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'The Python environment is missing. Follow the installation steps in README.md.'
}

$ffmpegRoot = Join-Path $PSScriptRoot '.tools\ffmpeg'
if (Test-Path -LiteralPath $ffmpegRoot) {
    $ffmpegBinary = Get-ChildItem -LiteralPath $ffmpegRoot -Filter ffmpeg.exe -Recurse |
        Select-Object -First 1
    if ($ffmpegBinary) {
        $env:PATH = "$($ffmpegBinary.DirectoryName);$env:PATH"
    }
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    throw 'FFmpeg is missing. Install FFmpeg and add its bin directory to PATH.'
}

& $pythonPath -m streamlit run app.py @args
exit $LASTEXITCODE
