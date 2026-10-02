# Windows installer

The public [releases page](https://github.com/notfeylo/modelmeter/releases/latest) contains the published installer for users. The per-user Inno Setup package contains a Tauri desktop executable and a frozen Python backend. It installs a Start Menu shortcut and optional desktop shortcut. The Tauri window starts the Python local HTTP server on a free `127.0.0.1` port. Closing the window stops the server. Running the shortcut a second time focuses the existing Modelmeter window.

## Build on Windows

Use Python 3.12, Node.js 22 or newer, Rust/MSVC, WebView2, and Inno Setup 6. Install Inno Setup with `winget install --id JRSoftware.InnoSetup --exact`. Then from the repo root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install pyinstaller==6.22.3 Pillow==12.3.0
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-windows.ps1 -Python .venv/Scripts/python.exe
```

The script installs frontend packages from the lockfile, builds the UI, renders the SVG-derived icon, freezes the Python backend, builds the Tauri shell, verifies Microsoft's signature on the WebView2 bootstrapper, and compiles `dist/Modelmeter-Setup-0.5.1-win-x64.exe`. Setup installs WebView2 per user if it is missing. That step requires internet access on PCs without WebView2. The GitHub CI Windows job builds the same installer, runs a desktop smoke check, and uploads it as a workflow artifact.

## Release verification

Before publishing a version, run Python tests, frontend lint and audit, and the Windows build. Install the setup file on Windows, launch the installed Start Menu shortcut, verify the native window, `/api/health`, and the dashboard, launch the shortcut again to confirm it focuses one running instance, then close the window. Publish the exact tested setup file and its SHA-256 hash in the GitHub release. Release tags and installer versions should match.

For upgrades from 0.2.0, quit the tray app before starting Setup. For later updates, close the current window first. If Setup detects a running instance, its default **Automatically close the applications** choice is the intended path; click **Next**. Inno Setup deliberately asks before closing an active application during an interactive install.

The installer currently has no code-signing certificate. Windows SmartScreen may prompt on download or first launch. Do not claim publisher verification or bypass security controls in the installer.
