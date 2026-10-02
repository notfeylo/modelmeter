param([string]$Executable = "src-tauri\target\release\Tallybeam.exe")

$ErrorActionPreference = "Stop"
$appPath = (Resolve-Path -LiteralPath $Executable).Path
$app = Start-Process -FilePath $appPath -PassThru
try {
    $healthy = $false
    for ($i = 0; $i -lt 60; $i++) {
        if ($app.HasExited) { throw "Desktop app exited before opening (code $($app.ExitCode))." }
        try {
            $backend = Get-CimInstance Win32_Process -Filter "name='TallybeamBackend.exe'" | Where-Object { $_.ParentProcessId -eq $app.Id } | Select-Object -First 1
            if (-not $backend -or $backend.CommandLine -notmatch '--port\s+(\d+)') { throw "Backend not ready" }
            $port = $Matches[1]
            $result = Invoke-RestMethod "http://127.0.0.1:$port/api/health" -TimeoutSec 1
            $app.Refresh()
            if ($result.ok -eq $true -and $result.version -eq "0.4.0" -and $app.MainWindowTitle -eq "Tallybeam") {
                $healthy = $true
                break
            }
        } catch {}
        Start-Sleep -Milliseconds 500
    }
    if (-not $healthy) { throw "Desktop app did not open a native window and healthy local service." }
    Write-Host "Desktop smoke passed: Tauri window and API $($result.version) on port $port."
} finally {
    if (-not $app.HasExited) {
        $app.CloseMainWindow() | Out-Null
        if (-not $app.WaitForExit(5000)) { Stop-Process -Id $app.Id -Force }
    }
    if ($backend) { Stop-Process -Id $backend.ProcessId -Force -ErrorAction SilentlyContinue }
}
