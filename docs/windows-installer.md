# Windows installer

The public [releases page](https://github.com/notfeylo/tallybeam/releases/latest) contains the published installer for users. The installer is a per-user Inno Setup package around a PyInstaller one-folder build. It installs a Start Menu shortcut and optional desktop shortcut. The launcher starts the Python local HTTP server and displays the dashboard inside its own Qt WebEngine window. Closing the window stops the server. The server binds only to `127.0.0.1`; if port 8765 is occupied by another app, the desktop launcher uses a free local port. Running the shortcut a second time focuses the existing Tallybeam window.

## Build on Windows

Use Python 3.12, Node.js 22, and Inno Setup 6. Install Inno Setup with `winget install --id JRSoftware.InnoSetup --exact`. Then from the repo root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install pyinstaller==6.22.3 Pillow==12.3.0 PySide6==6.11.2
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-windows.ps1 -Python .venv/Scripts/python.exe
```

The script installs frontend packages from the lockfile, builds the UI, renders the SVG-derived icons, bundles the Python app and Qt WebEngine, and compiles `dist/Tallybeam-Setup-0.3.0-win-x64.exe`. The GitHub CI Windows job builds the same installer and uploads it as a workflow artifact.

## Release verification

Before publishing a version, run Python tests, frontend lint and audit, and the Windows build. Install the setup file on Windows, launch the installed Start Menu shortcut, verify the native window, `/api/health`, and the dashboard, launch the shortcut again to confirm it focuses one running instance, then close the window. Publish the exact tested setup file and its SHA-256 hash in the GitHub release. Release tags and installer versions should match.

For upgrades from 0.2.0, quit the tray app before starting Setup. For later updates, close the Tallybeam window first. If Setup detects a running instance, its default **Automatically close the applications** choice is the intended path; click **Next**. Inno Setup deliberately asks before closing an active application during an interactive install.

The installer currently has no code-signing certificate. Windows SmartScreen may prompt on download or first launch. Do not claim publisher verification or bypass security controls in the installer.
