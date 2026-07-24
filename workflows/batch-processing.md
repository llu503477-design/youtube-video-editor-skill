# Workflow — Batch Processing

## Overview

批次處理大量影片的自動化工作流程。適用於：
- YouTube 頻道大量內容處理
- 教育課程影片批次字幕化
- Podcast 影片自動修剪與發布
- 社交媒體短片批量生產

## Batch Pipeline Script

```powershell
# batch-process.ps1 — Batch Video Processing
param(
    [Parameter(Mandatory=$true)]
    [string]$InputDir,          # 輸入目錄（含影片檔案）
    [string]$OutputDir = "output",
    [string]$BgmFile,           # 共用背景音樂（可選）
    [string]$WhisperModelPath = $env:WHISPER_CPP_MODEL,
    [string]$FilePattern = "*.mp4",  # 檔案過濾模式
    [string]$SubtitleLang = "zh",    # 字幕語言（預設繁體中文）
    [switch]$Recurse,            # 遞迴子目錄
    [switch]$Bilingual,          # 雙語字幕（zh-TW + EN）
    [switch]$AssFormat,          # 使用 ASS 格式（中文字大、英文字小）
    [ValidateSet('none','black')]
    [string]$SubBg = "black",    # 字幕背景: none (透明) 或 black (黑底包覆文字)
    [switch]$Narrate,            # 啟用旁白 (TTS voiceover)
    [string]$NarrateLang = "zh-TW",  # 旁白語言
    [string]$NarrateVoice,       # Edge-TTS 發音人
    [ValidateSet('intro','full','summary')]
    [string]$NarrateMode = "intro",  # 旁白模式
    [switch]$SilenceRemove,      # 啟用靜音移除
    [int]$MaxConcurrent = 1      # 最大並行數（預設為序）
)

$ErrorActionPreference = "Continue"

# 確保輸出目錄存在
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

# 收集要處理的檔案
$getParams = @{Path=$InputDir; Filter=$FilePattern}
if ($Recurse) { $getParams["Recurse"] = $true }
$files = Get-ChildItem @getParams

Write-Host "========================================"
Write-Host "Batch Video Processing"
Write-Host "========================================"
Write-Host "Found $($files.Count) files to process"
Write-Host ""

if ($files.Count -eq 0) {
    Write-Host "No files found matching pattern: $FilePattern in $InputDir"
    exit 1
}

$processed = 0
$failed = 0
$logFile = Join-Path $OutputDir "batch_log_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"

foreach ($file in $files) {
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
    $outputPath = Join-Path $OutputDir "${baseName}_processed.mp4"
    $srtPath = Join-Path $OutputDir "${baseName}.srt"
    $zhSrtPath = Join-Path $OutputDir "${baseName}.zh.srt"
    $enSrtPath = Join-Path $OutputDir "${baseName}.en.srt"
    $bilingualSrtPath = Join-Path $OutputDir "${baseName}.bilingual.srt"
    $assPath = Join-Path $OutputDir "${baseName}.bilingual.ass"

    Write-Host "[$($processed+$failed+1)/$($files.Count)] Processing: $($file.Name)" -ForegroundColor Cyan

    # Step 1: Silence removal (optional)
    $currentInput = $file.FullName
    if ($SilenceRemove) {
        $tempEdited = Join-Path $OutputDir "_temp_${baseName}.mp4"
        try {
            auto-editor $currentInput --edit audio:threshold:-20dB --output $tempEdited
            $currentInput = $tempEdited
            Write-Host "  -> Silence removed"
        } catch {
            Write-Host "  -> Auto-editor failed, using original" -ForegroundColor Yellow
        }
    }

    # Step 2: Audio extraction
    $audioFile = Join-Path $OutputDir "_temp_${baseName}.wav"
    try {
        ffmpeg -i $currentInput -vn -acodec pcm_s16le -ar 16000 -ac 1 $audioFile -y
        Write-Host "  -> Audio extracted"
    } catch {
        Write-Host "  -> Audio extraction failed" -ForegroundColor Red
        $failed++
        continue
    }

    # Step 3: Generate subtitles
    try {
        if ($Bilingual) {
            Write-Host "  -> Bilingual mode: transcribing Chinese (zh)..."
            & scripts/whisper-cli.ps1 $audioFile -ModelPath $WhisperModelPath -Language zh `
                -Task transcribe -OutputPrefix ([System.IO.Path]::ChangeExtension($zhSrtPath, $null)) 2>&1 | Out-Null

            Write-Host "  -> Translating to English..."
            & scripts/whisper-cli.ps1 $audioFile -ModelPath $WhisperModelPath -Language zh `
                -Task translate -OutputPrefix ([System.IO.Path]::ChangeExtension($enSrtPath, $null)) 2>&1 | Out-Null

            if ((Test-Path $zhSrtPath) -and (Test-Path $enSrtPath)) {
                if ($AssFormat) {
                    python scripts/generate_bilingual_ass.py $zhSrtPath $enSrtPath $assPath
                    Write-Host "  -> Bilingual ASS generated (zh 24px / en 18px)"
                } else {
                    python scripts/merge_bilingual_srt.py $zhSrtPath $enSrtPath $bilingualSrtPath
                    Write-Host "  -> Bilingual SRT merged"
                }
            }
        } else {
            & scripts/whisper-cli.ps1 $audioFile -ModelPath $WhisperModelPath -Language $SubtitleLang `
                -OutputPrefix ([System.IO.Path]::ChangeExtension($srtPath, $null)) 2>&1 | Out-Null
            Write-Host "  -> Subtitles generated"
        }
    } catch {
        Write-Host "  -> Subtitle generation failed (skipping)" -ForegroundColor Yellow
    }

    # Step 4: Add BGM and burn subtitles
    $buildArgs = @("-i", $currentInput)
    $filterComplex = ""
    $mapArgs = @()

    if ($BgmFile -and (Test-Path $BgmFile)) {
        $buildArgs += @("-i", $BgmFile)
        $filterComplex = "[1:a]volume=0.3[bgm];[0:a][bgm]amix=inputs=2:duration=shortest:dropout_transition=2[aout]"
        $mapArgs = @("-map", "0:v", "-map", "[aout]")
    } else {
        $mapArgs = @("-map", "0:v", "-map", "0:a")
    }

    # ── Dynamic font scaling based on video height ──
    $videoHeight = & ffprobe -v error -select_streams v:0 -show_entries stream=height -of default=noprint_wrappers=1:nokey=1 $currentInput 2>&1
    if (-not $videoHeight -or $videoHeight -le 0) { $videoHeight = 1080 }
    $refHeight = 1080
    $scaleFactor = [math]::Max(0.44, [math]::Min(4.0, [double]$videoHeight / $refHeight))
    $zhFontSize = [math]::Round(22 * $scaleFactor)
    $enFontSize = [math]::Round(16 * $scaleFactor)
    $marginV = [math]::Round(50 * $scaleFactor)

    # Build background style based on SubBg
    if ($SubBg -eq "black") {
        $bgStyle = "FontName=Noto Sans TC,FontSize=$zhFontSize,BackColour=&H80000000,BorderStyle=4,Outline=0,Shadow=0,MarginV=$marginV"
        $bgLabel = "black box (zh=${zhFontSize}px, scaled=$($scaleFactor.ToString('0.00')))"
    } else {
        $bgStyle = "FontName=Noto Sans TC,FontSize=$zhFontSize,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=$marginV,BorderStyle=1"
        $bgLabel = "transparent outline+shadow (zh=${zhFontSize}px, scaled=$($scaleFactor.ToString('0.00')))"
    }

    # ── Narration generation (optional) ──
    $narrationWav = $null
    if ($Narrate -and (Test-Path $srtPath)) {
        $narrationWav = Join-Path $OutputDir "${baseName}_narration.wav"
        Write-Host "  -> Generating narration ($NarrateLang, $NarrateMode)..."
        $narrateArgs = @("--subs", $srtPath, "--lang", $NarrateLang, "--mode", $NarrateMode, "--output", $narrationWav)
        if ($NarrateVoice) { $narrateArgs += @("--voice", $NarrateVoice) }
        python scripts/narrate.py @narrateArgs 2>&1 | Out-Null
        if (Test-Path $narrationWav) {
            Write-Host "  -> Narration generated: $narrationWav"
        } else {
            Write-Host "  -> Narration failed" -ForegroundColor Yellow
            $narrationWav = $null
        }
    }

    # Subtitle filter: ASS > bilingual SRT > monolingual SRT
    $subFilter = ""
    if ($Bilingual -and $AssFormat -and (Test-Path $assPath)) {
        $subFilter = "-vf", "ass=$assPath"
        Write-Host "  -> Burning bilingual ASS subtitles (zh=${zhFontSize}px / en=${enFontSize}px, auto-scaled)"
    } elseif ($Bilingual -and (Test-Path $bilingualSrtPath)) {
        $subFilter = "-vf", "subtitles=$bilingualSrtPath:force_style='$bgStyle'"
        Write-Host "  -> Burning bilingual SRT subtitles ($bgLabel)"
    } elseif (Test-Path $srtPath) {
        $subFilter = "-vf", "subtitles=$srtPath:force_style='FontName=Noto Sans TC,FontSize=$zhFontSize,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=$marginV,BorderStyle=1'"
        Write-Host "  -> Burning subtitles ($bgLabel)"
    }

    # If narration is available, use sidechain ducking instead of basic amix
    $narrationFilter = ""
    if ($narrationWav -and (Test-Path $narrationWav)) {
        # Add narration as input
        $buildArgs += @("-i", $narrationWav)
        $narrationIdx = $buildArgs.Count - 2  # Last -i argument pair
        # Base filter: narration duck original audio
        $narrationFilter = "[${narrationIdx}:a]adelay=2000|2000[narration];[0:a][narration]sidechaincompress=level_in=1:threshold=0.015:ratio=10:attack=100:release=500[ducked];[ducked][narration]amix=inputs=2:duration=first[aout_narr]"
    }

    if ($filterComplex -and $narrationFilter) {
        # Three-layer: narration duck + BGM
        $narrationIdx = $buildArgs.Count - 2
        $fullFilter = "${narrationFilter};[aout_narr][${narrationIdx}:a]amix=inputs=2:duration=first[aout]"
        & ffmpeg $buildArgs -filter_complex $fullFilter $subFilter -c:v libx264 -crf 23 -c:a aac $outputPath -y 2>&1 | Out-Null
    } elseif ($narrationFilter) {
        # Two-layer: narration duck original (no BGM)
        & ffmpeg $buildArgs -filter_complex $narrationFilter -map 0:v -map "[aout_narr]" $subFilter -c:v libx264 -crf 23 -c:a aac $outputPath -y 2>&1 | Out-Null
    } elseif ($filterComplex) {
        & ffmpeg $buildArgs -filter_complex $filterComplex $mapArgs $subFilter -c:v libx264 -crf 23 -c:a aac $outputPath -y 2>&1 | Out-Null
    } else {
        & ffmpeg $buildArgs $mapArgs $subFilter -c:v libx264 -crf 23 -c:a aac $outputPath -y 2>&1 | Out-Null
    }

    # Cleanup
    if (Test-Path $audioFile) { Remove-Item $audioFile -Force }
    if ($SilenceRemove -and (Test-Path $currentInput) -and $currentInput -ne $file.FullName) {
        Remove-Item $currentInput -Force
    }

    if (Test-Path $outputPath) {
        $outSize = (Get-Item $outputPath).Length
        $outSizeMB = [math]::Round($outSize / 1MB, 2)
        Write-Host "  -> ✅ Done: $outputPath (${outSizeMB}MB)" -ForegroundColor Green
        $processed++

        # 寫入日誌
        "$($file.Name) -> $outputPath" | Out-File $logFile -Append
    } else {
        Write-Host "  -> ❌ Failed to create output" -ForegroundColor Red
        $failed++
    }

    Write-Host ""
}

Write-Host "========================================"
Write-Host "Batch Processing Complete!"
Write-Host "========================================"
Write-Host "Total: $($files.Count), Processed: $processed, Failed: $failed"
Write-Host "Output directory: $OutputDir"
Write-Host "Log file: $logFile"
```

## Usage Examples

```powershell
# 批次處理目錄中所有 MP4
.\batch-process.ps1 -InputDir "D:\raw_videos" -OutputDir "D:\processed"

# 處理所有 MOV 檔案（含子目錄）
.\batch-process.ps1 -InputDir "D:\raw" -OutputDir "D:\processed" -FilePattern "*.mov" -Recurse

# 加入 BGM + 靜音移除
.\batch-process.ps1 -InputDir "D:\raw" -OutputDir "D:\processed" -BgmFile "D:\music\bgm.mp3" -SilenceRemove

# 使用 medium Whisper 模型
.\batch-process.ps1 -InputDir "D:\raw" -OutputDir "D:\processed" -WhisperModelPath $env:WHISPER_CPP_MODEL

# 雙語字幕批次（zh-TW + EN 合併 SRT）
.\batch-process.ps1 -InputDir "D:\raw" -OutputDir "D:\processed" -Bilingual

# 雙語字幕 + ASS 格式批次（中文 24px、英文 18px）
.\batch-process.ps1 -InputDir "D:\raw" -OutputDir "D:\processed" -Bilingual -AssFormat

# 完整處理：雙語 ASS + BGM + 靜音移除
.\batch-process.ps1 -InputDir "D:\raw" -OutputDir "D:\processed" -Bilingual -AssFormat -BgmFile "D:\music\bgm.mp3" -SilenceRemove

# 無黑底字幕（乾淨風格統一外觀）
.\batch-process.ps1 -InputDir "D:\raw" -OutputDir "D:\processed" -Bilingual -SubBg none

# 黑底字幕（高可讀性，僅包覆文字）
.\batch-process.ps1 -InputDir "D:\raw" -OutputDir "D:\processed" -Bilingual -SubBg black

# 批次旁白（繁體中文，階段性介紹）
.\batch-process.ps1 -InputDir "D:\raw" -OutputDir "D:\processed" -Bilingual -Narrate

# 批次旁白 + 英文發音
.\batch-process.ps1 -InputDir "D:\raw" -OutputDir "D:\processed" -Bilingual -Narrate -NarrateLang en -NarrateVoice en-US-AriaNeural

# 完整批次：雙語 + 旁白 + BGM + 靜音移除
.\batch-process.ps1 -InputDir "D:\raw" -OutputDir "D:\processed" -Bilingual -Narrate -NarrateLang zh-TW -BgmFile "D:\music\bgm.mp3" -SilenceRemove
```

## Batch Processing Strategies

### 策略 1: 完整批次（適用於大量同類型內容）

```
Input:  10 部教學影片
Process:
  1. 全部靜音移除
  2. 全部 Whisper 轉錄
  3. 全部加入共同 BGM
  4. 全部燒錄字幕
Output: 10 部處理完成的影片
```

### 策略 2: 分段批次（適用於長影片）

```
Input:  1 部 60 分鐘長片
Process:
  1. 分割為 12 個 5 分鐘片段
  2. 每段獨立處理
  3. 重新合併
Output: 1 部處理完成的長片
```

### 策略 3: 平行批次（需要多核心 CPU / GPU）

```
Input:  20 部短片
Process:
  1. 同時處理 4 部（使用 -MaxConcurrent 4）
  2. 每部獨立產線
Output: 20 部處理完成的影片
```

## Performance Considerations

| 因素 | 影響 | 建議 |
|------|------|------|
| CPU 核心數 | 轉碼速度 | 使用 `-t` 參數設定線程數 |
| GPU | 編碼加速 | NVENC 可加速 3-5x |
| VRAM | Whisper 模型大小 | medium=5GB, large=10GB |
| 磁碟 I/O | 讀寫速度 | 使用 SSD，分離來源/輸出目錄 |
| 檔案大小 | 磁碟空間 | 確保有 2-3x 原始大小的空間 |

## Error Handling

批次處理時，建議：
1. 先對 1-2 個樣本執行完整流程確認參數正確
2. 使用 `-ErrorAction Continue` 讓單一檔案失敗不中斷批次
3. 記錄日誌以便事後檢查失敗原因
4. 失敗的檔案可重新處理（腳本會跳過已存在的輸出）

## Quality Assurance

批次處理完成後：
```powershell
# 檢查所有輸出檔案
Get-ChildItem $OutputDir -Filter "*_processed.mp4" | ForEach-Object {
    $info = ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $_.FullName
    Write-Host "$($_.Name): ${info}s, $( [math]::Round($_.Length/1MB, 2) )MB"
}
```
