param(
    [string]$Version = "0.2.0",
    [string]$Iscc = "",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $root
try {
    $packageVersion = & $Python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"
    if ($LASTEXITCODE -ne 0 -or $packageVersion -ne $Version) { throw "Installer version must match pyproject.toml ($packageVersion)." }
    npm --prefix frontend ci
    if ($LASTEXITCODE -ne 0) { throw "npm ci failed" }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }

    & $Python scripts/make_icon.py
    if ($LASTEXITCODE -ne 0) { throw "Icon generation failed" }

    & $Python -m PyInstaller --noconfirm --clean --windowed --onedir --name Tallybeam --specpath build --icon "$root\assets\tallybeam.ico" --add-data "$root\tallybeam\static;tallybeam/static" --collect-all pystray "$root\desktop_entry.py"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

    if (-not $Iscc) {
        $found = Get-Command ISCC.exe -ErrorAction SilentlyContinue
        if ($found) { $Iscc = $found.Source }
    }
    if (-not $Iscc) {
        foreach ($candidate in @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe")) {
            if (Test-Path -LiteralPath $candidate) { $Iscc = $candidate; break }
        }
    }
    if (-not $Iscc) { throw "ISCC.exe not found. Install Inno Setup 6 or pass -Iscc." }
    & $Iscc "/DAppVersion=$Version" "installer/tallybeam.iss"
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed" }
    Write-Host "Installer: $root\dist\Tallybeam-Setup-$Version-win-x64.exe"
} finally {
    Pop-Location
}
