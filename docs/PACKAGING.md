# Packaging

This project packages with PyInstaller.

The app icon is stored in:

- `generated_assets/app-icon.icns` for macOS
- `generated_assets/app-icon.ico` for Windows
- `generated_assets/app-icon.png` for the Tkinter window icon

## Requirements

Install the app runtime dependencies and the packaging dependency:

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-packaging.txt
```

On Windows, use `python` instead of `python3` if that is how Python is installed.

## macOS Installer

Build on macOS:

```bash
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
```

Outputs:

- `dist/Harvest Opportunities.app`
- `dist/Harvest Opportunities-macOS.dmg`

## Windows Installer

Build on Windows PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\build_windows.ps1"
```

The one-process execution-policy bypass does not change the machine's permanent PowerShell policy.

The script installs the Python packaging dependencies, builds the app, and invokes Inno Setup. The output is:

- `dist\Harvest Opportunities-Windows-Setup.exe`

Python 3 and Inno Setup 6 must be installed on the Windows build machine:

https://www.python.org/downloads/windows/
https://jrsoftware.org/isinfo.php

The resulting setup installs per-user, so recipients do not need administrator access. It adds an uninstall entry and a Start-menu shortcut, and offers an optional desktop shortcut.

## Platform Note

Build each installer on its target operating system. A macOS machine can build the `.app` and `.dmg`; a Windows machine should build the `.exe` installer.
