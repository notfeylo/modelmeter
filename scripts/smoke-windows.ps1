param([string]$Executable = "dist\Tallybeam\Tallybeam.exe")

$ErrorActionPreference = "Stop"
$appPath = (Resolve-Path -LiteralPath $Executable).Path
$app = Start-Process -FilePath $appPath -PassThru
try {
    $healthy = $false
    for ($i = 0; $i -lt 60; $i++) {
        if ($app.HasExited) { throw "Desktop app exited before opening (code $($app.ExitCode))." }
        try {
            $result = Invoke-RestMethod "http://127.0.0.1:8765/api/health" -TimeoutSec 1
            $app.Refresh()
            if ($result.ok -eq $true -and $result.version -eq "0.3.0" -and $app.MainWindowTitle -eq "Tallybeam") {
                $healthy = $true
                break
            }
        } catch {}
        Start-Sleep -Milliseconds 500
    }
    if (-not $healthy) { throw "Desktop app did not open a native window and healthy local service." }
    Write-Host "Desktop smoke passed: native Tallybeam window and API $($result.version)."
} finally {
    if (-not $app.HasExited) { Stop-Process -Id $app.Id -Force }
}
