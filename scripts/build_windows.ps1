$ErrorActionPreference = "Stop"

$AppName = "Harvest Opportunities"
$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RootDir

function Find-Python {
  $PythonLauncher = Get-Command "py.exe" -ErrorAction SilentlyContinue
  if ($PythonLauncher) {
    & $PythonLauncher.Source -3 --version *> $null
    if ($LASTEXITCODE -eq 0) {
      return @($PythonLauncher.Source, "-3")
    }
  }

  $PythonCandidates = @(
    (Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA "Programs\Python\Python*\python.exe") -ErrorAction SilentlyContinue |
      Sort-Object FullName -Descending |
      Select-Object -ExpandProperty FullName),
    (Get-Command "python.exe" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
  ) | Where-Object { $_ }

  foreach ($PythonPath in $PythonCandidates) {
    & $PythonPath --version *> $null
    if ($LASTEXITCODE -eq 0) {
      return @($PythonPath)
    }
  }

  throw "Python 3 is not installed. Install it from https://www.python.org/downloads/windows/ and run this script again."
}

$PythonCommand = @(Find-Python)
$PythonExe = $PythonCommand[0]
$PythonArgs = @($PythonCommand | Select-Object -Skip 1)

Write-Host "Installing/updating packaging dependencies..."
& $PythonExe @PythonArgs -m pip install --disable-pip-version-check -r "requirements-packaging.txt"
if ($LASTEXITCODE -ne 0) {
  throw "Could not install the Python packaging dependencies."
}

$BuildDir = Join-Path $RootDir "build"
$AppDistDir = Join-Path $RootDir "dist\$AppName"
$ZipPath = Join-Path $RootDir "dist\$AppName-Windows.zip"
$InstallerPath = Join-Path $RootDir "dist\$AppName-Windows-Setup.exe"
$IconPath = Join-Path $RootDir "generated_assets\app-icon.ico"
$AssetsPath = Join-Path $RootDir "generated_assets"
$EntryPoint = Join-Path $RootDir "main.py"

Remove-Item -LiteralPath $BuildDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $AppDistDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $ZipPath -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $InstallerPath -Force -ErrorAction SilentlyContinue

$PyInstallerConfigDir = Join-Path ([System.IO.Path]::GetTempPath()) "harvest-opportunities-pyinstaller-$PID"
Remove-Item -LiteralPath $PyInstallerConfigDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $PyInstallerConfigDir | Out-Null
$env:PYINSTALLER_CONFIG_DIR = $PyInstallerConfigDir

Write-Host "Building the Windows application..."
try {
  & $PythonExe @PythonArgs -m PyInstaller `
    --noconfirm `
    --clean `
    --specpath "build" `
    --windowed `
    --name "$AppName" `
    --icon "$IconPath" `
    --add-data "$AssetsPath;generated_assets" `
    "$EntryPoint"
  if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed to build the application."
  }
} finally {
  Remove-Item -LiteralPath $PyInstallerConfigDir -Recurse -Force -ErrorAction SilentlyContinue
  Remove-Item Env:PYINSTALLER_CONFIG_DIR -ErrorAction SilentlyContinue
}

$IsccCommand = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
$IsccPath = if ($IsccCommand) { $IsccCommand.Source } else { $null }
if (-not $IsccPath) {
  $InnoCandidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe")
  )
  $IsccPath = $InnoCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
}

if (-not $IsccPath) {
  throw "Inno Setup 6 was not found. Install it from https://jrsoftware.org/isinfo.php and run this script again."
}

Write-Host "Building the Windows installer..."
& $IsccPath "installer\windows\VolunteerPadletWindows.iss"
if ($LASTEXITCODE -ne 0) {
  throw "Inno Setup failed to build the installer."
}

if (-not (Test-Path -LiteralPath $InstallerPath)) {
  throw "The build completed without producing the expected installer: $InstallerPath"
}

Write-Host "Built: $InstallerPath"
