# Synthesize one WAV per narration segment with Windows SAPI, and report the measured duration
# of each so the frame renderer can time the visuals to the actual speech rather than a guess.
#
# Rate -1 gives about 128 words per minute. Dynomap's reference track runs about 85 wpm once the
# pauses between segments are counted, so segments are padded to their scripted length in
# build.py rather than by slowing the voice further, which starts to sound dragged.
#
# Usage:  powershell -File narrate.ps1 -ScriptJson script.json -OutDir wav
param(
    [Parameter(Mandatory = $true)][string]$ScriptJson,
    [Parameter(Mandatory = $true)][string]$OutDir,
    [string]$Voice = "Microsoft Zira Desktop",
    [int]$Rate = -1
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$segments = (Get-Content -Raw -Path $ScriptJson | ConvertFrom-Json).segments
$report = @()

foreach ($seg in $segments) {
    $wav = Join-Path $OutDir ("seg{0:d2}.wav" -f [int]$seg.n)

    # A fresh synthesizer per segment: reusing one after SetOutputToWaveFile leaves the previous
    # file handle open on some builds, which truncates the last segment.
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    try {
        $synth.SelectVoice($Voice)
        $synth.Rate = $Rate
        $synth.SetOutputToWaveFile($wav)
        $synth.Speak($seg.narration)
    } finally {
        $synth.Dispose()
    }

    # 22.05 kHz, 16-bit, mono: 44 bytes of RIFF header, then 2 bytes per frame.
    $bytes = (Get-Item $wav).Length
    $seconds = [math]::Round(($bytes - 44) / (22050.0 * 2), 3)
    $words = ($seg.narration -split '\s+').Count

    $report += [pscustomobject]@{
        n         = [int]$seg.n
        wav       = $wav
        seconds   = $seconds
        scripted  = [double]$seg.seconds
        words     = $words
        wpm       = [math]::Round($words / $seconds * 60, 0)
    }
    Write-Output ("seg{0:d2}  {1,6:N2}s spoken / {2,5:N1}s scripted  {3,3} words  {4,3} wpm" -f `
        [int]$seg.n, $seconds, [double]$seg.seconds, $words, [math]::Round($words / $seconds * 60, 0))
}

$overrun = $report | Where-Object { $_.seconds -gt $_.scripted }
if ($overrun) {
    Write-Output ""
    Write-Output "WARNING: speech is longer than the scripted slot in these segments; build.py will"
    Write-Output "extend them to fit, which shifts every later caption cue:"
    $overrun | ForEach-Object { Write-Output ("  seg{0:d2}  {1:N2}s > {2:N1}s" -f $_.n, $_.seconds, $_.scripted) }
}

$report | ConvertTo-Json -Depth 3 | Set-Content -Encoding utf8 (Join-Path $OutDir "durations.json")
Write-Output ""
Write-Output ("total spoken: {0:N1}s across {1} segments" -f (($report | Measure-Object -Property seconds -Sum).Sum), $report.Count)
