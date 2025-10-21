# Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
# powershell -ExecutionPolicy ByPass -c "irm https://github.com/olivierfriard/BORIS/blob/master/deployment/windows_deployment.ps1 | iex"


# Download and extract standalone Python 3.13.9 build, then install boris-behav-obs via pip

$Url = "https://github.com/astral-sh/python-build-standalone/releases/download/20251014/cpython-3.13.9+20251014-x86_64-pc-windows-msvc-install_only_stripped.tar.gz"
$DownloadPath = "$env:TEMP\cpython-3.13.9.tar.gz"
$ExtractPath = "$env:USERPROFILE\BORIS"

# Remove existing target folder if it exists
if (Test-Path $ExtractPath) {
    Write-Host "Removing existing BORIS folder at $ExtractPath..."
    Remove-Item -Path $ExtractPath -Recurse -Force
}

# Create a fresh folder
New-Item -ItemType Directory -Force -Path $ExtractPath | Out-Null

Write-Host "Downloading Python build..."
Invoke-WebRequest -Uri $Url -OutFile $DownloadPath

Write-Host "Download complete. Extracting..."
& tar -xzf $DownloadPath -C $ExtractPath

# Find Python executable path
$PythonExe = Get-ChildItem -Path $ExtractPath -Recurse -Filter "python.exe" -ErrorAction SilentlyContinue | Select-Object -First 1

if (-Not $PythonExe) {
    Write-Error "❌ Python executable not found after extraction!"
    exit 1
}

Write-Host "Installing boris-behav-obs with pip..."
& "$($PythonExe.FullName)" -m ensurepip --upgrade
& "$($PythonExe.FullName)" -m pip install --upgrade pip
& "$($PythonExe.FullName)" -m pip install boris-behav-obs


# Remove unused files
Remove-Item -Path $ExtractPath\python\tcl -Recurse -Force
Remove-Item -Path $ExtractPath\python\include -Recurse -Force
Remove-Item -Path $ExtractPath\python\share -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\ensurepip -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\pydoc_data -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\tkinter -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\turtledemo -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\venv -Recurse -Force
Remove-Item -Path $ExtractPath\python\Scripts -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\glue -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\plugins\geoservices -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\plugins\multimedia   -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\plugins\qmltooling -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\plugins\sensors -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\plugins\sqldrivers -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\plugins\texttospeech -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\qml -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\translations -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\assistant.exe -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\designer.exe -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\linguist.exe -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\qmlformat.exe -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\Qt6Quick.dll -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\Qt6Pdf.dll -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\Qt6Designer.dll -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\Qt6Qml.dll -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\Qt6Quick3DRuntimeRender.dll -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\Qt6WebEngineCore.dll -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\Qt6WebEngineQuick.dll -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\Qt6WebEngineQuickDelegatesQml.dll -Recurse -Force
Remove-Item -Path $ExtractPath\python\Lib\site-packages\PySide6\Qt6WebEngineWidgets.dll -Recurse -Force



Write-Host "`n✅ Installation complete!"
Write-Host "Python executable located at: $($PythonExe.FullName)"
Write-Host "BORIS installed in: $ExtractPath"
Write-Host "`nTo launch BORIS, run:"
Write-Host "`"$($PythonExe.FullName)`" -m boris"

# Get BORIS version (supports x.y or x.y.z)
Write-Host "Retrieving BORIS version..."
$BorisVersionOutput = & "$($PythonExe.FullName)" -m boris -v 2>$null
$BorisVersion = ($BorisVersionOutput | Select-String -Pattern '\b\d+\.\d+(?:\.\d+)?\b').Matches.Value


if (-not $BorisVersion) {
    Write-Warning "⚠️ Could not determine BORIS version, defaulting to 'unknown'"
    $BorisVersion = "unknown"
}

Write-Host "Detected BORIS version: $BorisVersion"

# Launch BORIS
Write-Host "`nLaunching BORIS..."
& "$($PythonExe.FullName)" -m boris -q -n -f

# After BORIS exits, compress folder
$ZipPath = "$env:USERPROFILE\BORIS-$BorisVersion.zip"

if (Test-Path $ZipPath) {
    Write-Host "Removing existing archive $ZipPath..."
    Remove-Item -Path $ZipPath -Force
}

Compress-Archive -Path $ExtractPath -DestinationPath $ZipPath -Force -CompressionLevel Optimal

Write-Host "`n✅ BORIS folder compressed successfully!"
Write-Host "ZIP archive created at: $ZipPath"
