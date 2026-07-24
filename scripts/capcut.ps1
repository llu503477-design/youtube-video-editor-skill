#!/usr/bin/env pwsh
# capcut.ps1 — CapCut-like CLI for video editing (FFmpeg backend)
#
# Provides intuitive commands similar to CapCut's GUI workflow,
# powered entirely by FFmpeg. Zero GUI required — scriptable pipelines.
#
# Usage:
#   .\capcut.ps1 help                          # Show this help
#   .\capcut.ps1 trim input.mp4 -start 00:30 -end 01:30 -o out.mp4
#   .\capcut.ps1 split input.mp4 -at 00:45
#   .\capcut.ps1 merge "part1.mp4,part2.mp4" -o merged.mp4
#   .\capcut.ps1 text input.mp4 -t "Hello World" -o out.mp4
#   .\capcut.ps1 audio input.mp4 -bgm bgm.mp3 -o out.mp4
#   .\capcut.ps1 speed input.mp4 -rate 2.0 -o out.mp4
#   .\capcut.ps1 subtitle input.mp4 -srt subs.srt -o out.mp4
#   .\capcut.ps1 export input.mp4 -o final.mp4
#
# Author: YouTube Video Editor Skill
# Backend: FFmpeg (required)

param(
    # === SUBCOMMAND (positional) ===
    [Parameter(Position = 0)]
    [ValidateSet("help", "trim", "split", "merge", "text", "audio", "speed", "subtitle", "export", "info")]
    [string]$Command = "help",

    # === GLOBAL PARAMS ===
    [Parameter(Position = 1)]
    [Alias("Input", "i")]
    [string]$Source,

    [Parameter(Position = 2)]
    [Alias("o")]
    [string]$Output,

    # === OPERATION-SPECIFIC PARAMS ===
    [string]$Start,
    [string]$End,
    [string]$At,
    [Alias("t")]
    [string]$Text,
    [string]$Bg,
    [string]$Bgm,
    [string]$Srt,
    [string]$FontName = "Noto Sans TC",
    [int]$FontSize = 22,
    [double]$Rate = 1.0,
    [switch]$Quiet,
    [switch]$Force
)

# ── FFMPEG CHECK ──
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    Write-Host "[ERROR] FFmpeg not found. Install FFmpeg and add to PATH." -ForegroundColor Red
    exit 1
}
$script:OverwriteFlag = if ($Force) { "-y" } else { "-n" }

function Assert-OutputAvailable {
    param([string]$Path)
    if ((Test-Path -LiteralPath $Path) -and -not $Force) {
        Write-Host "[ERROR] Output already exists: $Path. Use -Force to overwrite it." -ForegroundColor Red
        exit 1
    }
}

function Invoke-FfmpegCommand {
    param(
        [string[]]$Arguments,
        [string]$Operation
    )

    $output = & ffmpeg @Arguments 2>&1
    if ($LASTEXITCODE -eq 0) {
        return $true
    }

    Write-Host "  [capcut] ERROR: $Operation failed (ffmpeg exit $LASTEXITCODE)" -ForegroundColor Red
    if (-not $Quiet) {
        $output | Select-Object -Last 12 | ForEach-Object { Write-Host "    $_" }
    }
    return $false
}

# ── HELPER: Resolve input file ──
function Resolve-PathOrUrl {
    param([string]$Path)
    if ($Path -match '^https?://') { return $Path }
    if (-not (Test-Path $Path)) {
        Write-Host "[ERROR] File not found: $Path" -ForegroundColor Red
        exit 1
    }
    return (Resolve-Path $Path).Path
}

function ConvertTo-FilterPath {
    param([string]$Path)
    return ($Path.Replace('\', '/').Replace(':', '\:').Replace("'", "\'"))
}

function Escape-FilterText {
    param([string]$Value)
    return ($Value.Replace('\', '\\').Replace("'", "\'").Replace(':', '\:').Replace('%', '\%'))
}

function Test-HasAudioStream {
    param([string]$Path)
    $ffprobe = Get-Command ffprobe -ErrorAction SilentlyContinue
    if (-not $ffprobe) {
        Write-Host "[ERROR] FFprobe is required to inspect audio streams." -ForegroundColor Red
        exit 1
    }
    $stream = & $ffprobe.Source -v error -select_streams a:0 -show_entries stream=index -of csv=p=0 $Path 2>$null
    return $LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace(($stream -join ""))
}

function Get-AtempoFilter {
    param([double]$Tempo)
    $parts = [System.Collections.Generic.List[string]]::new()
    $remaining = $Tempo

    while ($remaining -lt 0.5) {
        $parts.Add("atempo=0.5")
        $remaining /= 0.5
    }
    while ($remaining -gt 100.0) {
        $parts.Add("atempo=100")
        $remaining /= 100.0
    }

    $formatted = $remaining.ToString("0.########", [System.Globalization.CultureInfo]::InvariantCulture)
    $parts.Add("atempo=$formatted")
    return $parts -join ","
}

# ── HELPER: Default output ──
function Get-OutPath {
    param([string]$InputPath, [string]$Suffix, [string]$Ext = ".mp4")
    $dir = Split-Path $InputPath -Parent
    $base = [System.IO.Path]::GetFileNameWithoutExtension($InputPath)
    if (-not $dir) { $dir = "." }
    return Join-Path $dir "${base}_${Suffix}${Ext}"
}

# ── SUBCOMMAND: help ──
function Show-Help {
    Write-Host @"

  ╔══════════════════════════════════════════════════════╗
  ║        CapCut-like CLI — FFmpeg Backend             ║
  ╚══════════════════════════════════════════════════════╝

  USAGE:
    .\capcut.ps1 <command> <input> [options]

  COMMANDS:

    trim    剪輯片段              -start 00:30 -end 01:30 -o out.mp4
    split   分割影片              -at 00:45
    merge   合併多段影片          "part1.mp4,part2.mp4" -o merged.mp4
    text    加入文字標題/浮水印   -t "標題文字" -o out.mp4
    audio   加入/取代背景音樂     -bgm music.mp3 -o out.mp4
    speed   調整播放速度          -rate 2.0 -o out.mp4
    subtitle燒錄字幕              -srt caption.srt -o out.mp4
    export  匯出最終影片          -o final.mp4
    info    顯示影片資訊

  EXAMPLES:

    # 剪輯片段
    .\capcut.ps1 trim video.mp4 -start 00:01:30 -end 00:03:00 -o clip.mp4

    # 加入大字標題（左上方）
    .\capcut.ps1 text video.mp4 -t "超強解說" -o titled.mp4

    # 加入背景音樂（音量 30%）
    .\capcut.ps1 audio video.mp4 -bgm bgm.mp3 -o with_bgm.mp4

    # 快轉 2 倍
    .\capcut.ps1 speed video.mp4 -rate 2.0 -o fast.mp4

    # 燒錄字幕
    .\capcut.ps1 subtitle video.mp4 -srt subtitle.srt -o subbed.mp4

  NOTES:
    - All commands fall back to pure FFmpeg (no external dependencies beyond FFmpeg)
    - Audio-only files work with all commands (trim/split/merge/speed)
    - For batch operations, wrap in foreach: Get-ChildItem *.mp4 | foreach { ... }

"@
}

# ── SUBCOMMAND: trim ──
function Invoke-Trim {
    param($InputPath, $OutPath)
    $resolved = Resolve-PathOrUrl $InputPath
    if (-not $OutPath) { $OutPath = Get-OutPath $InputPath "trim" }
    Assert-OutputAvailable $OutPath

    $args = @($script:OverwriteFlag, "-i", $resolved)
    if ($Start) { $args += @("-ss", $Start) }
    if ($End) { $args += @("-to", $End) }
    $args += @("-c:v", "libx264", "-crf", "23", "-c:a", "aac", "-map", "0", $OutPath)

    Write-Host "  [capcut] trim: $InputPath → $OutPath" -ForegroundColor Cyan
    if ($Start) { Write-Host "    -start $Start" }
    if ($End) { Write-Host "    -end $End" }
    $succeeded = Invoke-FfmpegCommand -Arguments $args -Operation "trim"
    if ($succeeded -and (Test-Path -LiteralPath $OutPath)) {
        Write-Host "  [capcut] OK: $OutPath" -ForegroundColor Green
    } else {
        exit 1
    }
}

# ── SUBCOMMAND: split ──
function Invoke-Split {
    param($InputPath)
    $resolved = Resolve-PathOrUrl $InputPath
    if (-not $At) { Write-Host "[ERROR] Use -at to specify split time" -ForegroundColor Red; exit 1 }

    $dir = Split-Path $resolved -Parent
    $base = [System.IO.Path]::GetFileNameWithoutExtension($InputPath)
    if (-not $dir) { $dir = "." }

    $part1 = Join-Path $dir "${base}_part1.mp4"
    $part2 = Join-Path $dir "${base}_part2.mp4"
    Assert-OutputAvailable $part1
    Assert-OutputAvailable $part2

    Write-Host "  [capcut] split: $InputPath at $At" -ForegroundColor Cyan

    # Part 1: before $At
    $part1Ok = Invoke-FfmpegCommand -Arguments @($script:OverwriteFlag, "-i", $resolved, "-ss", "0", "-to", $At, "-c:v", "libx264", "-crf", "23", "-c:a", "aac", "-map", "0", $part1) -Operation "split part 1"
    # Part 2: after $At
    $part2Ok = Invoke-FfmpegCommand -Arguments @($script:OverwriteFlag, "-i", $resolved, "-ss", $At, "-c:v", "libx264", "-crf", "23", "-c:a", "aac", "-map", "0", $part2) -Operation "split part 2"

    if ($part1Ok -and $part2Ok -and (Test-Path -LiteralPath $part1) -and (Test-Path -LiteralPath $part2)) {
        Write-Host "  [capcut] OK: $part1" -ForegroundColor Green
        Write-Host "  [capcut] OK: $part2" -ForegroundColor Green
        Write-Host "  [capcut] Tip: merge with 'capcut merge \"$part1,$part2\" -o combined.mp4'" -ForegroundColor Yellow
    } else {
        exit 1
    }
}

# ── SUBCOMMAND: merge (concat) ──
function Invoke-Merge {
    param($InputList, $OutPath)
    if (-not $OutPath) { $OutPath = "merged.mp4" }
    Assert-OutputAvailable $OutPath
    if ([string]::IsNullOrWhiteSpace($InputList)) {
        Write-Host "[ERROR] Provide at least two comma-separated input files." -ForegroundColor Red
        exit 1
    }

    # InputList: comma-separated file paths
    $files = $InputList.Split(',') | ForEach-Object { $_.Trim() }
    Write-Host "  [capcut] merge: $($files.Count) files → $OutPath" -ForegroundColor Cyan

    # Method: concat demuxer (fast, no re-encode if compatible)
    $listFile = Join-Path ([System.IO.Path]::GetTempPath()) "capcut_concat_$([System.IO.Path]::GetRandomFileName()).txt"
    $resolvedFiles = @()
    $allOk = $true
    foreach ($f in $files) {
        try {
            $resolved = Resolve-PathOrUrl $f
            "file '$($resolved -replace "'","'\\''")'" | Add-Content $listFile -Encoding UTF8
            $resolvedFiles += $resolved
        } catch {
            Write-Host "  [capcut] ERROR: cannot access $f" -ForegroundColor Red
            $allOk = $false
        }
    }

    if ($allOk -and $resolvedFiles.Count -ge 2) {
        $mergeOk = Invoke-FfmpegCommand -Arguments @($script:OverwriteFlag, "-f", "concat", "-safe", "0", "-i", $listFile, "-c:v", "libx264", "-crf", "23", "-c:a", "aac", "-map", "0", $OutPath) -Operation "merge"
        Remove-Item $listFile -Force -ErrorAction SilentlyContinue
        if ($mergeOk -and (Test-Path -LiteralPath $OutPath)) {
            Write-Host "  [capcut] OK: $OutPath" -ForegroundColor Green
        } else {
            exit 1
        }
    } else {
        Write-Host "  [capcut] ERROR: need at least 2 files to merge" -ForegroundColor Red
        Remove-Item $listFile -Force -ErrorAction SilentlyContinue
        exit 1
    }
}

# ── SUBCOMMAND: text (drawtext overlay) ──
function Invoke-Text {
    param($InputPath, $OutPath)
    $resolved = Resolve-PathOrUrl $InputPath
    if (-not $Text) { Write-Host "[ERROR] Use -t/Text to specify text content" -ForegroundColor Red; exit 1 }
    if (-not $OutPath) { $OutPath = Get-OutPath $InputPath "texted" }
    Assert-OutputAvailable $OutPath
    $escapedText = Escape-FilterText $Text
    $escapedFont = Escape-FilterText $FontName

    Write-Host "  [capcut] text: '$Text' over $InputPath → $OutPath" -ForegroundColor Cyan
    Write-Host "    Font: $FontName, Size: ${FontSize}px"

    # drawtext filter: bottom-left with outline+shadow
    $textOk = Invoke-FfmpegCommand -Arguments @(
        $script:OverwriteFlag, "-i", $resolved,
        "-vf", "drawtext=font='$escapedFont':text='$escapedText':fontsize=$FontSize`:fontcolor=white:bordercolor=black:borderw=3:x=30:y=h-th-30:shadowx=3:shadowy=3:shadowcolor=black@0.6",
        "-c:v", "libx264", "-crf", "23", "-c:a", "aac", "-map", "0", $OutPath
    ) -Operation "text overlay"

    if ($textOk -and (Test-Path -LiteralPath $OutPath)) {
        Write-Host "  [capcut] OK: $OutPath" -ForegroundColor Green
    } else {
        exit 1
    }
}

# ── SUBCOMMAND: audio (replace/bgm mix) ──
function Invoke-Audio {
    param($InputPath, $OutPath)
    $resolved = Resolve-PathOrUrl $InputPath
    if (-not $OutPath) { $OutPath = Get-OutPath $InputPath "with_audio" }
    Assert-OutputAvailable $OutPath

    if ($Bgm) {
        $bgmResolved = Resolve-PathOrUrl $Bgm
        Write-Host "  [capcut] audio: BGM '$Bgm' + $InputPath → $OutPath" -ForegroundColor Cyan
        if (Test-HasAudioStream $resolved) {
            # Mix BGM at 30% volume with original audio.
            $audioOk = Invoke-FfmpegCommand -Arguments @(
                $script:OverwriteFlag, "-i", $resolved, "-i", $bgmResolved,
                "-filter_complex", "[1:a]volume=0.3[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                "-map", "0:v:0", "-map", "[aout]", "-c:v", "libx264", "-crf", "23", "-c:a", "aac", "-shortest", $OutPath
            ) -Operation "audio mix"
        } else {
            # A silent source has nothing to mix; attach the BGM as its audio track.
            $audioOk = Invoke-FfmpegCommand -Arguments @(
                $script:OverwriteFlag, "-i", $resolved, "-stream_loop", "-1", "-i", $bgmResolved,
                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-crf", "23",
                "-c:a", "aac", "-shortest", $OutPath
            ) -Operation "attach background music"
        }
    } else {
        Write-Host "  [capcut] audio: replace audio track in $InputPath" -ForegroundColor Cyan
        Write-Host "  [capcut] Tip: use -bgm to add background music, or use FFmpeg directly to replace audio" -ForegroundColor Yellow
        # Just copy with re-encode
        $audioOk = Invoke-FfmpegCommand -Arguments @($script:OverwriteFlag, "-i", $resolved, "-c:v", "libx264", "-crf", "23", "-c:a", "aac", $OutPath) -Operation "audio transcode"
    }

    if ($audioOk -and (Test-Path -LiteralPath $OutPath)) {
        Write-Host "  [capcut] OK: $OutPath" -ForegroundColor Green
    } else {
        exit 1
    }
}

# ── SUBCOMMAND: speed ──
function Invoke-Speed {
    param($InputPath, $OutPath)
    $resolved = Resolve-PathOrUrl $InputPath
    if (-not $OutPath) { $OutPath = Get-OutPath $InputPath "sped" }
    Assert-OutputAvailable $OutPath
    if ($Rate -le 0) {
        Write-Host "[ERROR] -Rate must be greater than zero." -ForegroundColor Red
        exit 1
    }

    Write-Host "  [capcut] speed: ${Rate}x — $InputPath → $OutPath" -ForegroundColor Cyan

    # setpts for video, atempo for audio
    $videoRate = (1 / $Rate).ToString("0.########", [System.Globalization.CultureInfo]::InvariantCulture)
    $videoFilter = "setpts=${videoRate}*PTS"
    $audioFilter = Get-AtempoFilter $Rate

    $speedOk = Invoke-FfmpegCommand -Arguments @(
        $script:OverwriteFlag, "-i", $resolved,
        "-filter_complex", "[0:v]$videoFilter[vout];[0:a]$audioFilter[aout]",
        "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-crf", "23", "-c:a", "aac", $OutPath
    ) -Operation "speed change"

    if ($speedOk -and (Test-Path -LiteralPath $OutPath)) {
        Write-Host "  [capcut] OK: $OutPath" -ForegroundColor Green
    } else {
        exit 1
    }
}

# ── SUBCOMMAND: subtitle (burn SRT) ──
function Invoke-Subtitle {
    param($InputPath, $OutPath)
    $resolved = Resolve-PathOrUrl $InputPath
    if (-not $Srt) { Write-Host "[ERROR] Use -srt to specify subtitle file" -ForegroundColor Red; exit 1 }
    $srtResolved = Resolve-PathOrUrl $Srt
    if (-not $OutPath) { $OutPath = Get-OutPath $InputPath "subbed" }
    Assert-OutputAvailable $OutPath
    $filterSrt = ConvertTo-FilterPath $srtResolved
    $escapedFont = Escape-FilterText $FontName

    Write-Host "  [capcut] subtitle: '$Srt' → $InputPath → $OutPath" -ForegroundColor Cyan

    $subtitleOk = Invoke-FfmpegCommand -Arguments @(
        $script:OverwriteFlag, "-i", $resolved,
        "-vf", "subtitles='$filterSrt':force_style='FontName=$escapedFont,FontSize=$FontSize,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=50,BorderStyle=1'",
        "-c:v", "libx264", "-crf", "23", "-c:a", "aac", "-map", "0", $OutPath
    ) -Operation "subtitle burn"

    if ($subtitleOk -and (Test-Path -LiteralPath $OutPath)) {
        Write-Host "  [capcut] OK: $OutPath" -ForegroundColor Green
    } else {
        exit 1
    }
}

# ── SUBCOMMAND: export (just copy with re-encode for compatibility) ──
function Invoke-Export {
    param($InputPath, $OutPath)
    $resolved = Resolve-PathOrUrl $InputPath
    if (-not $OutPath) { $OutPath = Get-OutPath $InputPath "final" }
    Assert-OutputAvailable $OutPath

    Write-Host "  [capcut] export: $InputPath → $OutPath" -ForegroundColor Cyan

    $exportOk = Invoke-FfmpegCommand -Arguments @($script:OverwriteFlag, "-i", $resolved, "-c:v", "libx264", "-crf", "23", "-c:a", "aac", "-map", "0", $OutPath) -Operation "export"

    if ($exportOk -and (Test-Path -LiteralPath $OutPath)) {
        $size = (Get-Item $OutPath).Length
        Write-Host "  [capcut] OK: $OutPath ($([math]::Round($size/1MB, 2))MB)" -ForegroundColor Green
    } else {
        exit 1
    }
}

# ── SUBCOMMAND: info (ffprobe summary) ──
function Invoke-Info {
    param($InputPath)
    $resolved = Resolve-PathOrUrl $InputPath
    if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
        Write-Host "[ERROR] FFprobe not found. Install FFmpeg and add FFprobe to PATH." -ForegroundColor Red
        exit 1
    }

    Write-Host ""
    Write-Host "  ═══════════════ Video Info ═══════════════" -ForegroundColor Cyan
    & ffprobe -v quiet -print_format json -show_format -show_streams $resolved | ConvertFrom-Json | ForEach-Object {
        $format = $_.format
        Write-Host "  File:       $(Split-Path $format.filename -Leaf)"
        Write-Host "  Format:     $($format.format_name)"
        Write-Host "  Duration:   $([math]::Round([double]$format.duration, 2))s"
        Write-Host "  Bitrate:    $([math]::Round([double]$format.bit_rate/1000, 0)) kbps"
        Write-Host "  Size:       $([math]::Round([double]$format.size/1MB, 2)) MB"

        foreach ($stream in $_.streams) {
            if ($stream.codec_type -eq "video") {
                Write-Host "  ─ Video ─"
                Write-Host "    Codec:    $($stream.codec_name)"
                Write-Host "    Resol:    $($stream.width)x$($stream.height)"
                Write-Host "    FPS:      $($stream.r_frame_rate)"
                if ($stream.bit_rate) {
                    Write-Host "    Bitrate:  $([math]::Round([double]$stream.bit_rate/1000, 0)) kbps"
                }
            }
            if ($stream.codec_type -eq "audio") {
                Write-Host "  ─ Audio ─"
                Write-Host "    Codec:    $($stream.codec_name)"
                Write-Host "    Sample:   $($stream.sample_rate) Hz"
                Write-Host "    Channel:  $($stream.channels)"
            }
        }
    }
    Write-Host "  ═══════════════════════════════════════════" -ForegroundColor Cyan
}

# ── MAIN DISPATCH ──
switch ($Command.ToLower()) {
    "help"     { Show-Help }
    "trim"     { Invoke-Trim $Source $Output }
    "split"    { Invoke-Split $Source }
    "merge"    { Invoke-Merge $Source $Output }
    "text"     { Invoke-Text $Source $Output }
    "audio"    { Invoke-Audio $Source $Output }
    "speed"    { Invoke-Speed $Source $Output }
    "subtitle" { Invoke-Subtitle $Source $Output }
    "export"   { Invoke-Export $Source $Output }
    "info"     { Invoke-Info $Source }
    default    { Show-Help }
}
