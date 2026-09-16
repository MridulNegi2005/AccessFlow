param([string]$RuntimeDirectory = 'D:\AccessFlow-LocalRuntime')
$ErrorActionPreference = 'Stop'
$recordPath = Join-Path ([IO.Path]::GetFullPath($RuntimeDirectory)) 'ollama-server.json'
$record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
$server = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
if (-not $server) { Write-Output 'The recorded Ollama process has already exited.'; exit 0 }
if ($server.Path -ne $record.executable -or
    $server.StartTime.ToUniversalTime() -ne ([datetime]$record.started_utc).ToUniversalTime()) {
    throw 'The recorded PID now belongs to a different process; nothing was stopped.'
}
$endpoint = [uri]$record.url
if ($endpoint.Scheme -ne 'http' -or $endpoint.Host -ne '127.0.0.1' -or
    $endpoint.AbsolutePath -ne '/' -or $endpoint.Query -or $endpoint.UserInfo) {
    throw 'The recorded endpoint is not a project loopback URL.'
}
$listeners = @(Get-NetTCPConnection -LocalPort $endpoint.Port -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count -eq 0 -or ($listeners | Where-Object OwningProcess -ne $server.Id)) {
    throw 'The recorded endpoint is not served by the verified project process.'
}
$loaded = Invoke-RestMethod -Uri "$($record.url)/api/ps" -TimeoutSec 3
if (-not ($loaded.PSObject.Properties.Name -contains 'models')) { throw 'Invalid loaded-model response.' }
foreach ($model in $loaded.models) {
    $body = @{model=$model.name; keep_alive=0; stream=$false} | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri "$($record.url)/api/generate" -ContentType 'application/json' `
        -Body $body -TimeoutSec 30 | Out-Null
}
$remaining = Invoke-RestMethod -Uri "$($record.url)/api/ps" -TimeoutSec 3
if (-not ($remaining.PSObject.Properties.Name -contains 'models') -or @($remaining.models).Count -ne 0) {
    throw 'Model unload was not confirmed; the server was not stopped.'
}
Stop-Process -InputObject $server -Force
if (-not $server.WaitForExit(5000)) { throw 'The project server did not exit after stop.' }
$record | Add-Member -NotePropertyName state -NotePropertyValue 'stopped' -Force
$record | Add-Member -NotePropertyName stopped_utc -NotePropertyValue ([datetime]::UtcNow.ToString('o')) -Force
$record | ConvertTo-Json | Set-Content -LiteralPath $recordPath -Encoding UTF8
Write-Output 'Unloaded models and stopped the verified project Ollama process.'
