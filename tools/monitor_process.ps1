# Sample an existing Shrimply process without opening its camera or changing settings.
param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 2147483647)]
    [int]$ProcessId,
    [ValidateRange(1, 86400)]
    [int]$Seconds = 7200,
    [ValidateRange(1, 60)]
    [int]$IntervalSeconds = 5,
    [string]$OutputPath = "diagnostics/resources-$ProcessId.csv"
)

$ErrorActionPreference = 'Stop'
$destination = [IO.Path]::GetFullPath($OutputPath)
if (Test-Path -LiteralPath $destination) { throw "Report already exists: $destination" }
$targetProcess = Get-Process -Id $ProcessId
$startedAt = $targetProcess.StartTime
$parentDirectory = Split-Path -Parent $destination
New-Item -ItemType Directory -Path $parentDirectory -Force | Out-Null
$watch = [Diagnostics.Stopwatch]::StartNew()
$lastElapsed = 0.0
$lastCpu = $targetProcess.CPU

Write-Host "Sampling process $ProcessId for $Seconds seconds. Report: $destination"
while ($watch.Elapsed.TotalSeconds -lt $Seconds) {
    try { $targetProcess = Get-Process -Id $ProcessId -ErrorAction Stop }
    catch { Write-Host 'Process exited; sampling complete.'; break }
    if ($targetProcess.StartTime -ne $startedAt) {
        Write-Host 'Process ID was reused; sampling stopped.'
        break
    }
    $elapsed = $watch.Elapsed.TotalSeconds
    $cpu = $targetProcess.CPU
    $cpuPercent = if ($elapsed -gt $lastElapsed -and $lastElapsed -gt 0) {
        100 * ($cpu - $lastCpu) / ($elapsed - $lastElapsed)
    } else { $null }
    [pscustomobject]@{
        utc = [DateTime]::UtcNow.ToString('o')
        elapsed_s = [math]::Round($elapsed, 3)
        cpu_one_core_pct = if ($null -ne $cpuPercent) { [math]::Round($cpuPercent, 2) } else { $null }
        working_set_mb = [math]::Round($targetProcess.WorkingSet64 / 1MB, 2)
        private_mb = [math]::Round($targetProcess.PrivateMemorySize64 / 1MB, 2)
        handles = $targetProcess.HandleCount
        threads = $targetProcess.Threads.Count
    } | Export-Csv -LiteralPath $destination -Append -NoTypeInformation -Encoding UTF8
    $lastElapsed = $elapsed
    $lastCpu = $cpu
    $remaining = $Seconds - $watch.Elapsed.TotalSeconds
    if ($remaining -gt 0) {
        Start-Sleep -Milliseconds ([int](1000 * [math]::Min($IntervalSeconds, $remaining)))
    }
}
