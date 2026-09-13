param(
    [string]$RuntimeDirectory = 'D:\AccessFlow-LocalRuntime',
    [ValidateRange(1024, 65535)][int]$Port = 11435
)
$ErrorActionPreference = 'Stop'
$runtimePath = [IO.Path]::GetFullPath($RuntimeDirectory)
$executable = Join-Path $runtimePath 'ollama-v0.34.0\ollama.exe'
if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw 'Install the verified portable Ollama archive first; see docs/LOCAL_MODELS.md.'
}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $Port already has a listener; this script will not replace it."
}
$modelDirectory = Join-Path $runtimePath 'models'
New-Item -ItemType Directory -Path $modelDirectory -Force | Out-Null
$env:OLLAMA_MODELS = $modelDirectory
$env:OLLAMA_HOST = "127.0.0.1:$Port"
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:OLLAMA_CONTEXT_LENGTH = '4096'
$env:OLLAMA_KEEP_ALIVE = '5m'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$stdout = Join-Path $runtimePath "ollama-$stamp.stdout.log"
$stderr = Join-Path $runtimePath "ollama-$stamp.stderr.log"
$server = Start-Process -FilePath $executable -ArgumentList 'serve' -PassThru -WindowStyle Hidden `
    -WorkingDirectory $runtimePath -RedirectStandardOutput $stdout -RedirectStandardError $stderr
$record = [ordered]@{
    pid = $server.Id
    started_utc = $server.StartTime.ToUniversalTime().ToString('o')
    executable = $executable
    url = "http://127.0.0.1:$Port"
    models = $modelDirectory
    stdout = $stdout
    stderr = $stderr
}
$record | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimePath 'ollama-server.json') -Encoding UTF8
$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    $server.Refresh()
    if ($server.HasExited) { throw "Ollama exited during startup. Inspect $stderr" }
    try {
        $version = Invoke-RestMethod -Uri "$($record.url)/api/version" -TimeoutSec 1
        $ready = $true
        break
    } catch { Start-Sleep -Milliseconds 250 }
}
if (-not $ready) { throw "Ollama did not become ready. Its PID and logs are in $runtimePath\ollama-server.json" }
$record['version'] = $version.version
$record | ConvertTo-Json
