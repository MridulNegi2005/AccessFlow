param(
    [string]$RuntimeDirectory = 'D:\AccessFlow-LocalRuntime',
    [ValidateRange(1024, 65535)][int]$Port = 11435,
    # Flash attention is required for a quantized KV cache and frees VRAM for more layers.
    [ValidateSet('0', '1')][string]$FlashAttention = '0',
    [ValidateSet('f16', 'q8_0', 'q4_0')][string]$KvCacheType = 'f16',
    [ValidateRange(512, 32768)][int]$ContextLength = 4096
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
$env:OLLAMA_CONTEXT_LENGTH = "$ContextLength"
$env:OLLAMA_FLASH_ATTENTION = $FlashAttention
$env:OLLAMA_KV_CACHE_TYPE = $KvCacheType
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
    context_length = $ContextLength
    flash_attention = $FlashAttention
    kv_cache_type = $KvCacheType
    stdout = $stdout
    stderr = $stderr
    state = 'starting'
}
$recordPath = Join-Path $runtimePath 'ollama-server.json'
try {
    $record | ConvertTo-Json | Set-Content -LiteralPath $recordPath -Encoding UTF8
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        $server.Refresh()
        if ($server.HasExited) { throw "Ollama exited during startup. Inspect $stderr" }
        $listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
        if ($listeners | Where-Object OwningProcess -ne $server.Id) {
            throw 'Another process acquired the requested port during startup.'
        }
        if ($listeners.Count -gt 0) {
            try {
                $version = Invoke-RestMethod -Uri "$($record.url)/api/version" -TimeoutSec 1
                if (-not $version.version) { throw 'Missing server version' }
                $ready = $true
                break
            } catch { }
        }
        Start-Sleep -Milliseconds 250
    }
    if (-not $ready) { throw "Ollama did not become ready. Inspect $stderr" }
    $record['version'] = $version.version
    $record['state'] = 'ready'
    $record | ConvertTo-Json | Set-Content -LiteralPath $recordPath -Encoding UTF8
} catch {
    $startupError = $_
    $server.Refresh()
    if (-not $server.HasExited) {
        Stop-Process -InputObject $server -Force
        if (-not $server.WaitForExit(5000)) { throw 'Startup failed and the launched process did not exit.' }
    }
    $record['state'] = 'startup_failed_stopped'
    $record | ConvertTo-Json | Set-Content -LiteralPath $recordPath -Encoding UTF8
    throw $startupError
}
$record | ConvertTo-Json
