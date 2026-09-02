# Release Installers

The user-ready distribution is organized in:

- `Harvest Opportunities - Installers/START HERE.txt`
- `Harvest Opportunities - Installers/Windows/Harvest Opportunities Setup.exe`
- `Harvest Opportunities - Installers/macOS/Harvest Opportunities.dmg`

Share the generated `Harvest Opportunities - Windows and macOS Installers.zip`
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
