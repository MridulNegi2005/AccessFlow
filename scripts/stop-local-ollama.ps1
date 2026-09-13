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
$loaded = Invoke-RestMethod -Uri "$($record.url)/api/ps" -TimeoutSec 3
foreach ($model in $loaded.models) {
    $body = @{model=$model.name; keep_alive=0; stream=$false} | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri "$($record.url)/api/generate" -ContentType 'application/json' `
        -Body $body -TimeoutSec 30 | Out-Null
}
Stop-Process -Id $server.Id
Write-Output 'Unloaded models and stopped the verified project Ollama process.'
