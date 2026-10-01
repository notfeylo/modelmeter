# Windows installer

The public [releases page](https://github.com/notfeylo/tallybeam/releases/latest) contains the published installer for users. The installer is a per-user Inno Setup package around a PyInstaller one-folder build. It installs a Start Menu shortcut and optional desktop shortcut. The launcher starts the Python local HTTP server, opens the default browser, and provides a system tray menu to open or quit. The server binds only to `127.0.0.1`; if port 8765 is occupied by another app, the launcher uses a free local port.

## Build on Windows

Use Python 3.12, Node.js 22, and Inno Setup 6. Install Inno Setup with `winget install --id JRSoftware.InnoSetup --exact`. Then from the repo root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install pyinstaller==6.22.3 pystray==0.19.5 Pillow==12.3.0
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-windows.ps1 -Python .venv/Scripts/python.exe
```

The script installs frontend packages from the lockfile, builds the UI, renders the SVG-derived icons, bundles the Python app and assets, and compiles `dist/Tallybeam-Setup-0.2.0-win-x64.exe`. The GitHub CI Windows job builds the same installer and uploads it as a workflow artifact.

## Release verification

Before publishing a version, run Python tests, frontend lint and audit, and the Windows build. Install the setup file on Windows, launch the installed Start Menu shortcut, verify `/api/health` and the dashboard, launch the shortcut again to confirm it reopens one running instance, then quit from the tray. Publish the exact tested setup file and its SHA-256 hash in the GitHub release. Release tags and installer versions should match.

On updates, quit the running app from the tray before starting Setup. If Setup detects a running Tallybeam instance, its default **Automatically close the applications** choice is the intended path; click **Next**. Inno Setup deliberately asks before closing an active application during an interactive install.

The installer currently has no code-signing certificate. Windows SmartScreen may prompt on download or first launch. Do not claim publisher verification or bypass security controls in the installer.
