<#
.SYNOPSIS
  Downloads the external tools bundled with YTDownloader into .\bin

.DESCRIPTION
  - FFmpeg + FFprobe ("essentials" build, gyan.dev) - needed to merge/convert.
  - Deno (official release) - JavaScript runtime yt-dlp needs for YouTube.
  Every archive is checked against the SHA-256 published by its source.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\fetch_binaries.ps1
  powershell -ExecutionPolicy Bypass -File scripts\fetch_binaries.ps1 -DenoVersion 2.5.6
#>
param(
    [string]$DenoVersion = "latest",
    [string]$OutDir = (Join-Path $PSScriptRoot "..\bin")
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # Invoke-WebRequest is much faster without it
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Get-Text([string]$Url) {
    $r = Invoke-WebRequest -Uri $Url -UseBasicParsing
    if ($r.Content -is [byte[]]) { return [Text.Encoding]::UTF8.GetString($r.Content) }
    return [string]$r.Content
}

function Assert-Sha256([string]$File, [string]$Expected) {
    $Expected = ($Expected.Trim() -split '\s+')[0].ToLowerInvariant()
    $actual = (Get-FileHash -Algorithm SHA256 -Path $File).Hash.ToLowerInvariant()
    if ($actual -ne $Expected) {
        throw "SHA-256 mismatch for $(Split-Path $File -Leaf): expected $Expected, got $actual"
    }
    Write-Host "  sha256 OK ($actual)"
}

$OutDir = [IO.Path]::GetFullPath($OutDir)
New-Item -ItemType Directory -Force -Path $OutDir, (Join-Path $OutDir "licenses") | Out-Null
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("ytd-bin-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmp | Out-Null

try {
    # ── FFmpeg ───────────────────────────────────────────────────────
    $ffUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    Write-Host "Downloading FFmpeg: $ffUrl"
    $ffZip = Join-Path $tmp "ffmpeg.zip"
    Invoke-WebRequest -Uri $ffUrl -OutFile $ffZip -UseBasicParsing
    Assert-Sha256 $ffZip (Get-Text "$ffUrl.sha256")

    $ffDir = Join-Path $tmp "ffmpeg"
    Expand-Archive -Path $ffZip -DestinationPath $ffDir
    foreach ($name in "ffmpeg.exe", "ffprobe.exe") {
        $src = Get-ChildItem -Path $ffDir -Recurse -Filter $name | Select-Object -First 1
        if (-not $src) { throw "$name not found in the FFmpeg archive" }
        Copy-Item $src.FullName (Join-Path $OutDir $name) -Force
    }
    $ffLicense = Get-ChildItem -Path $ffDir -Recurse -Filter "LICENSE*" | Select-Object -First 1
    if ($ffLicense) { Copy-Item $ffLicense.FullName (Join-Path $OutDir "licenses\FFmpeg-LICENSE.txt") -Force }
    $ffReadme = Get-ChildItem -Path $ffDir -Recurse -Filter "README.txt" | Select-Object -First 1
    if ($ffReadme) { Copy-Item $ffReadme.FullName (Join-Path $OutDir "licenses\FFmpeg-README.txt") -Force }

    # ── Deno ─────────────────────────────────────────────────────────
    $asset = "deno-x86_64-pc-windows-msvc.zip"
    if ($DenoVersion -eq "latest") {
        $denoBase = "https://github.com/denoland/deno/releases/latest/download"
    } else {
        $denoBase = "https://github.com/denoland/deno/releases/download/v$($DenoVersion.TrimStart('v'))"
    }
    Write-Host "Downloading Deno: $denoBase/$asset"
    $denoZip = Join-Path $tmp $asset
    Invoke-WebRequest -Uri "$denoBase/$asset" -OutFile $denoZip -UseBasicParsing
    Assert-Sha256 $denoZip (Get-Text "$denoBase/$asset.sha256sum")
    Expand-Archive -Path $denoZip -DestinationPath (Join-Path $tmp "deno")
    Copy-Item (Join-Path $tmp "deno\deno.exe") (Join-Path $OutDir "deno.exe") -Force
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/denoland/deno/main/LICENSE.md" `
        -OutFile (Join-Path $OutDir "licenses\Deno-LICENSE.md") -UseBasicParsing

    # ── Summary ──────────────────────────────────────────────────────
    Write-Host ""
    Write-Host "Binaries in ${OutDir}:"
    & (Join-Path $OutDir "ffmpeg.exe") -hide_banner -version | Select-Object -First 1
    & (Join-Path $OutDir "deno.exe") --version | Select-Object -First 1
    Get-ChildItem $OutDir -File | ForEach-Object {
        "{0,-12} {1,8:N1} MB" -f $_.Name, ($_.Length / 1MB)
    }
}
finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
