# Release Installers

The user-ready distribution is organized in:

- `Volunteer Padlet Automation - Installers/START HERE.txt`
- `Volunteer Padlet Automation - Installers/Windows/Volunteer Padlet Automation Setup.exe`
- `Volunteer Padlet Automation - Installers/macOS/Volunteer Padlet Automation.dmg`

Share the generated `Volunteer Padlet Automation - Windows and macOS Installers.zip`
when both platforms should be distributed together.

Installer binaries and ZIP archives are ignored by Git and should be uploaded
to a GitHub Release, not committed to the repository.

Build commands:

```bash
./scripts/build_macos.sh
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\build_windows.ps1"
```
