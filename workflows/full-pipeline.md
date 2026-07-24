# Workflow — Full Production Pipeline

## Overview

從原始影片到最終出版的完整自動化產線。
包含：下載 → 自動剪輯 → 雙語字幕生成（zh-TW + EN）→ 燒錄字幕 → 加入 BGM → 輸出。

**字幕預設**：繁體中文（zh-TW）為上排（FontSize=22，1080p 基準），英文為下排（FontSize=16）。
字型 **Noto Sans TC**（Google 開源可商用），動態偵測影片高度自動縮放字級。

## Pipeline Stages

```
Stage 1: Download / Input
  │
  ▼
Stage 2: Pre-processing (Trim, Crop)
  │
  ▼
Stage 3: Auto Editing (Silence Removal)
  │
  ▼
Stage 4: Subtitle Generation
  │  ├─ Monolingual: Whisper(zh) → SRT
  │  └─ Bilingual:  Whisper(zh transcribe) + Whisper(zh→en translate)
  │                 → Merge → bilingual SRT / ASS (zh 22px + en 16px @1080p, auto-scaled)
  ▼
Stage 5: Narration Generation (Optional)
  │  ├─ narrate.py: subtitles → per-segment narration script
  │  ├─ Edge-TTS: zh-TW / en / ja / ko...
  │  └─ --mode intro: stage-by-stage guide
  ▼
Stage 6: Audio Mixing
  │  ├─ Original audio + BGM (basic mix)
  │  └─ + Narration (auto-duck via sidechaincompress)
  ▼
Stage 7: Subtitle Burning
  │  ├─ SRT: subtitles= force_style (uniform size)
  │  └─ ASS: ass= (per-language font sizes)
  ▼
Stage 8: Final Output
```

## Complete Pipeline Script

### PowerShell Script

```powershell
# full-pipeline.ps1 — YouTube Video Editor Full Pipeline
param(
    [Parameter(Mandatory=$true)]
    [string]$InputVideo,    # Local file path or YouTube URL
    [string]$BgmFile,       # Background music file (optional)
    [string]$OutputDir = ".",
    [string]$WhisperModelPath = $env:WHISPER_CPP_MODEL,
    [string]$SubtitleLang = "zh",  # Default language for bilingual subs
    [switch]$Bilingual,     # Generate zh-TW + EN bilingual subtitles
    [switch]$AssFormat,     # Use ASS format (different font sizes for zh/en)
    [ValidateSet('none','black')]
    [string]$SubBg = "black",  # Subtitle background: none (transparent) or black (box behind text)
    [switch]$Narrate,         # Enable narration (TTS voiceover from subtitles)
    [string]$NarrateLang = "zh-TW",  # Narration language (zh-TW, en, ja, etc.)
    [string]$NarrateVoice,    # Edge-TTS voice (auto-detected from NarrateLang if not set)
    [ValidateSet('intro','full','summary')]
    [string]$NarrateMode = "intro",  # Narration mode
    [string]$NarrateScript,   # Custom narration script (optional, overrides auto-generation)
    [switch]$SkipAutoEdit,
    [switch]$IsYouTubeUrl
)

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$workDir = Join-Path $OutputDir "work_$timestamp"
New-Item -ItemType Directory -Path $workDir -Force | Out-Null

# Filenames
$rawVideo = Join-Path $workDir "raw.mp4"
$trimmedVideo = Join-Path $workDir "trimmed.mp4"
$editedVideo = Join-Path $workDir "edited.mp4"
$audioFile = Join-Path $workDir "audio.wav"
$srtFile = Join-Path $workDir "subtitles.srt"
$zhSrtFile = Join-Path $workDir "subtitles.zh.srt"
$enSrtFile = Join-Path $workDir "subtitles.en.srt"
$bilingualSrtFile = Join-Path $workDir "subtitles.bilingual.srt"
$assFile = Join-Path $workDir "subtitles.bilingual.ass"
$narrationWav = Join-Path $workDir "narration.wav"
$bgmVideo = Join-Path $workDir "with_bgm.mp4"
$finalVideo = Join-Path $OutputDir "final_$timestamp.mp4"

Write-Host "========================================"
Write-Host "YouTube Video Editor - Full Pipeline"
Write-Host "========================================"
Write-Host ""

# ── Stage 1: Download / Input ──
Write-Host "[Stage 1/7] Acquiring source..." -ForegroundColor Cyan

if ($IsYouTubeUrl) {
    Write-Host "Downloading from YouTube..."
    yt-dlp -f "bestvideo+bestaudio" --merge-output-format mp4 -o $rawVideo $InputVideo
    if (-not (Test-Path $rawVideo)) {
        Write-Host "ERROR: Download failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "Downloaded: $rawVideo"
} else {
    $rawVideo = $InputVideo
    if (-not (Test-Path $rawVideo)) {
        Write-Host "ERROR: Input file not found: $rawVideo" -ForegroundColor Red
        exit 1
    }
    Write-Host "Using local file: $rawVideo"
}

# ── Stage 2: Pre-processing ──
Write-Host "`n[Stage 2/7] Pre-processing (trim check)..." -ForegroundColor Cyan
$duration = & ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $rawVideo 2>&1
Write-Host "Input duration: $([math]::Round([double]$duration, 2))s"
Write-Host "(Skipping trim - edit trim parameters in this section if needed)"
Copy-Item $rawVideo $trimmedVideo

# ── Stage 3: Auto Editing ──
Write-Host "`n[Stage 3/7] Auto editing (silence removal)..." -ForegroundColor Cyan
if (-not $SkipAutoEdit) {
    # Check if auto-editor is available
    $hasAutoEditor = & auto-editor --version 2>&1 | Select-String "auto-editor"
    if ($hasAutoEditor) {
        Write-Host "Using auto-editor..."
        auto-editor $trimmedVideo --edit audio:threshold:-20dB --output $editedVideo
    } else {
        Write-Host "auto-editor not found. Using FFmpeg silencedetect..."
        # FFmpeg-based silence detection
        & ffmpeg -i $trimmedVideo -af silencedetect=n=-25dB:d=0.8 -f null - 2> (Join-Path $workDir "silence.log")
        # (簡化版本：直接複製，實際需根據偵測結果建立 filter 指令)
        Copy-Item $trimmedVideo $editedVideo
        Write-Host "WARNING: FFmpeg silence removal is a placeholder. Install auto-editor for full functionality." -ForegroundColor Yellow
    }
} else {
    Copy-Item $trimmedVideo $editedVideo
    Write-Host "Auto-editing skipped."
}

# ── Stage 4: Subtitle Generation ──
Write-Host "`n[Stage 4/7] Generating subtitles (Whisper)..." -ForegroundColor Cyan

# Extract audio
Write-Host "Extracting audio..."
ffmpeg -i $editedVideo -vn -acodec pcm_s16le -ar 16000 -ac 1 $audioFile -y

# Check the project wrapper and globally installed whisper.cpp CLI
$whisperScript = Join-Path (Get-Location) "scripts\whisper-cli.ps1"
$hasWhisper = (Test-Path -LiteralPath $whisperScript) -and
    [bool](Get-Command whisper-cli -ErrorAction SilentlyContinue)
if ($hasWhisper) {
    if ($Bilingual) {
        # ── Bilingual pipeline: zh-TW (transcribe) + EN (translate) ──
        Write-Host "Bilingual mode enabled: generating zh-TW + EN subtitles..."

        # Step A: Chinese transcription (zh)
        Write-Host "Transcribing Chinese (zh)..."
        & $whisperScript $audioFile -ModelPath $WhisperModelPath -Language zh -Task transcribe `
            -OutputPrefix ([System.IO.Path]::ChangeExtension($zhSrtFile, $null))
        Write-Host "Chinese SRT: $zhSrtFile"

        # Step B: English translation (zh → en)
        Write-Host "Translating to English..."
        & $whisperScript $audioFile -ModelPath $WhisperModelPath -Language zh -Task translate `
            -OutputPrefix ([System.IO.Path]::ChangeExtension($enSrtFile, $null))
        Write-Host "English SRT: $enSrtFile"

        # Step C: Merge bilingual subtitle file
        if ((Test-Path $zhSrtFile) -and (Test-Path $enSrtFile)) {
            if ($AssFormat) {
                Write-Host "Generating bilingual ASS (Chinese 24px, English 18px)..."
                python scripts/generate_bilingual_ass.py $zhSrtFile $enSrtFile $assFile
                Write-Host "Bilingual ASS: $assFile"
            } else {
                Write-Host "Merging bilingual SRT..."
                python scripts/merge_bilingual_srt.py $zhSrtFile $enSrtFile $bilingualSrtFile
                Write-Host "Bilingual SRT: $bilingualSrtFile"
            }
        }
    } else {
        # ── Monolingual pipeline (single language) ──
        Write-Host "Transcribing with whisper.cpp (language=$SubtitleLang)..."
        & $whisperScript $audioFile -ModelPath $WhisperModelPath -Language $SubtitleLang `
            -OutputPrefix ([System.IO.Path]::ChangeExtension($srtFile, $null))
    }
} else {
    Write-Host "Whisper not found. Checking for FFmpeg 8.0+ whisper filter..." -ForegroundColor Yellow
    $hasFFmpegWhisper = & ffmpeg -filters 2>&1 | Select-String "whisper"
    if ($hasFFmpegWhisper) {
        Write-Host "Using FFmpeg 8.0+ native whisper filter..."
        ffmpeg -i $editedVideo -af "whisper=model='$WhisperModelPath':language=$SubtitleLang:format=srt" -f null -
        $generatedSrt = [System.IO.Path]::ChangeExtension($editedVideo, ".srt")
        if (Test-Path $generatedSrt) {
            Move-Item $generatedSrt $srtFile -Force
        }
    } else {
        Write-Host "WARNING: No transcription tool available. Skipping subtitle generation." -ForegroundColor Yellow
        Write-Host "Install: pwsh -File scripts/install-whisper-cpp.ps1" -ForegroundColor Cyan
    }
}

# ── Stage 5: Narration Generation (Optional) ──
if ($Narrate) {
    Write-Host "`n[Stage 5/8] Generating narration (TTS voiceover)..." -ForegroundColor Cyan

    # Determine which subtitle file to use for narration (priority: bilingual SRT > monolingual SRT > ASS)
    $narrationSubFile = $null
    if ($Bilingual -and (Test-Path $bilingualSrtFile)) {
        $narrationSubFile = $bilingualSrtFile
    } elseif (Test-Path $srtFile) {
        $narrationSubFile = $srtFile
    } elseif ($AssFormat -and (Test-Path $assFile)) {
        # ASS not directly supported for narrate.py; convert ASS to SRT first
        $narrationSubFile = Join-Path $workDir "subtitles_for_narr.srt"
        ffmpeg -i $assFile $narrationSubFile -y 2>&1 | Out-Null
    } else {
        # Try to generate subtitles first from audio
        if (Test-Path $audioFile) {
            Write-Host "  No subtitles found. Attempting Whisper transcription first..."
            & $whisperScript $audioFile -ModelPath $WhisperModelPath -Language $SubtitleLang `
                -OutputPrefix ([System.IO.Path]::ChangeExtension($srtFile, $null)) 2>&1 | Out-Null
            $narrationSubFile = $srtFile
        }
    }

    if ($NarrateScript -and (Test-Path $NarrateScript)) {
        # Custom narration script
        Write-Host "  Using custom narration script: $NarrateScript"
        python scripts/narrate.py --script $NarrateScript --lang $NarrateLang --mode $NarrateMode --output $narrationWav
    } elseif ($narrationSubFile -and (Test-Path $narrationSubFile)) {
        Write-Host "  Generating narration from: $narrationSubFile"
        $narrateArgs = @("--subs", $narrationSubFile, "--lang", $NarrateLang, "--mode", $NarrateMode, "--output", $narrationWav)
        if ($NarrateVoice) { $narrateArgs += @("--voice", $NarrateVoice) }
        python scripts/narrate.py @narrateArgs
    } else {
        Write-Host "  WARNING: No subtitles or script available for narration. Skipping." -ForegroundColor Yellow
    }

    if (Test-Path $narrationWav) {
        Write-Host "  ✅ Narration generated: $narrationWav" -ForegroundColor Green
        $hasNarration = $true
    } else {
        Write-Host "  WARNING: Narration generation failed." -ForegroundColor Yellow
        $hasNarration = $false
    }
} else {
    $hasNarration = $false
    $narrationWav = $null
}

# ── Stage 6: Audio Mixing ──
Write-Host "`n[Stage 6/8] Audio mixing..." -ForegroundColor Cyan

if ($hasNarration -and (Test-Path $narrationWav)) {
    Write-Host "  Mixing: original audio + narration (auto-duck) + BGM"

    if ($BgmFile -and (Test-Path $BgmFile)) {
        # Three-layer mix: narration duck original audio + BGM
        ffmpeg -i $editedVideo -i $narrationWav -i $BgmFile `
            -filter_complex `
            "[1:a]adelay=2000|2000[narration];`
             [0:a][narration]sidechaincompress=level_in=1:threshold=0.015:ratio=8:attack=100:release=500[ducked];`
             [2:a]volume=0.12[bgm];`
             [ducked][narration]amix=inputs=2:duration=first[mix1];`
             [mix1][bgm]amix=inputs=2:duration=first:weights=1 0.15[aout]" `
            -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k $bgmVideo -y
        Write-Host "  -> Mix complete: narration duck original + BGM at 12%"
    } else {
        # Two-layer mix: narration duck original audio
        ffmpeg -i $editedVideo -i $narrationWav `
            -filter_complex `
            "[1:a]adelay=2000|2000[narration];`
             [0:a][narration]sidechaincompress=level_in=1:threshold=0.015:ratio=10:attack=100:release=500:makeup=0[ducked];`
             [ducked][narration]amix=inputs=2:duration=first:weights=1 1[aout]" `
            -map 0:v -map "[aout]" -c:v copy -c:a aac $bgmVideo -y
        Write-Host "  -> Mix complete: narration duck original audio"
    }
} elseif ($BgmFile -and (Test-Path $BgmFile)) {
    Write-Host "  Adding background music: $BgmFile"
    ffmpeg -i $editedVideo -i $BgmFile -filter_complex "[1:a]volume=0.3[bgm];[0:a][bgm]amix=inputs=2:duration=shortest:dropout_transition=2[aout]" -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k $bgmVideo -y
} else {
    Write-Host "  No BGM or narration. Using original audio."
    $bgmVideo = $editedVideo
}

# ── Stage 7: Subtitle Burning ──
Write-Host "`n[Stage 7/8] Burning subtitles..." -ForegroundColor Cyan

# Build subtitle force_style based on background mode (for non-ASS subtitles)
# ── Dynamic Font Scaling based on video height ──
$videoHeight = & ffprobe -v error -select_streams v:0 -show_entries stream=height -of default=noprint_wrappers=1:nokey=1 $finalTrim 2>&1
if (-not $videoHeight -or $videoHeight -le 0) { $videoHeight = 1080 }
$refHeight = 1080
$scaleFactor = [math]::Max(0.44, [math]::Min(4.0, [double]$videoHeight / $refHeight))
$zhFontSize = [math]::Round(22 * $scaleFactor)
$enFontSize = [math]::Round(16 * $scaleFactor)
$marginV = [math]::Round(50 * $scaleFactor)
Write-Host "  Video height: ${videoHeight}px → font scale: $($scaleFactor.ToString('0.00')) → zh=${zhFontSize}px, en=${enFontSize}px"

if ($SubBg -eq "black") {
    $bgStyle = "FontName=Noto Sans TC,FontSize=$zhFontSize,BackColour=&H80000000,BorderStyle=4,Outline=0,Shadow=0,MarginV=$marginV"
    Write-Host "  SubBg=black: black box behind text (width wraps text only)"
} else {
    $bgStyle = "FontName=Noto Sans TC,FontSize=$zhFontSize,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=$marginV,BorderStyle=1"
    Write-Host "  SubBg=none: transparent background (outline+shadow only)"
}

# Determine subtitle source (priority: ASS > bilingual SRT > monolingual SRT)
$subSource = $null
if ($Bilingual -and $AssFormat -and (Test-Path $assFile)) {
    $subSource = $assFile
    $subFilter = "ass=$assFile"
    Write-Host "Using bilingual ASS subtitle (zh-TW ${zhFontSize}px / EN ${enFontSize}px, auto-scaled): $assFile"
} elseif ($Bilingual -and (Test-Path $bilingualSrtFile)) {
    $subSource = $bilingualSrtFile
    $subFilter = "subtitles=$bilingualSrtFile:force_style='$bgStyle'"
    Write-Host "Using bilingual SRT subtitle: $bilingualSrtFile"
} elseif (Test-Path $srtFile) {
    $subSource = $srtFile
    $subFilter = "subtitles=$srtFile:force_style='FontName=Noto Sans TC,FontSize=$zhFontSize,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=$marginV,BorderStyle=1'"
    Write-Host "Using monolingual SRT subtitle: $srtFile"
}

if ($subSource) {
    ffmpeg -i $bgmVideo -vf $subFilter -c:v libx264 -crf 23 -c:a copy $finalVideo -y
} else {
    Write-Host "No subtitles to burn. Copying video directly."
    Copy-Item $bgmVideo $finalVideo
}

# ── Stage 8: Output ──
Write-Host "`n[Stage 8/8] Final output..." -ForegroundColor Cyan
if (Test-Path $finalVideo) {
    $finalDuration = & ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $finalVideo 2>&1
    $finalSize = (Get-Item $finalVideo).Length
    $finalSizeMB = [math]::Round($finalSize / 1MB, 2)

    Write-Host ""
    Write-Host "========================================"
    Write-Host "✅ Pipeline Complete!" -ForegroundColor Green
    Write-Host "========================================"
    Write-Host "Final output: $finalVideo"
    Write-Host "Duration: $([math]::Round([double]$finalDuration, 2))s"
    Write-Host "Size: ${finalSizeMB}MB"

    # 清理工作目錄
    Remove-Item $workDir -Recurse -Force
    Write-Host "Temporary files cleaned up."
} else {
    Write-Host "ERROR: Pipeline failed - output file not created" -ForegroundColor Red
    Write-Host "Check logs in: $workDir" -ForegroundColor Yellow
    exit 1
}
```

### Usage

```powershell
# 基本用法（本地檔案）
.\full-pipeline.ps1 -InputVideo "D:\videos\raw.mp4"

# 加入 BGM
.\full-pipeline.ps1 -InputVideo "D:\videos\raw.mp4" -BgmFile "D:\music\bgm.mp3"

# 從 YouTube 下載並處理
.\full-pipeline.ps1 -InputVideo "https://youtube.com/watch?v=xxx" -IsYouTubeUrl

# 跳過自動剪輯
.\full-pipeline.ps1 -InputVideo "raw.mp4" -SkipAutoEdit

# 指定 Whisper 模型和輸出目錄
.\full-pipeline.ps1 -InputVideo "raw.mp4" -WhisperModelPath $env:WHISPER_CPP_MODEL -OutputDir "D:\output"

# 雙語字幕模式（zh-TW + EN 合併 SRT，統一風格）
.\full-pipeline.ps1 -InputVideo "raw.mp4" -Bilingual

# 雙語字幕 + ASS 格式（自動偵測解析度，動態字級縮放）
.\full-pipeline.ps1 -InputVideo "raw.mp4" -Bilingual -AssFormat

# 無黑底字幕（乾淨風格，透明背景）
.\full-pipeline.ps1 -InputVideo "raw.mp4" -Bilingual -SubBg none

# 黑底字幕（僅包覆文字，非全螢幕寬，預設）
.\full-pipeline.ps1 -InputVideo "raw.mp4" -Bilingual -SubBg black

# 從 YouTube 下載 + 雙語字幕 + BGM
.\full-pipeline.ps1 -InputVideo "https://youtube.com/watch?v=xxx" -IsYouTubeUrl -Bilingual -AssFormat -BgmFile "D:\music\bgm.mp3"

# 加入旁白（繁體中文，階段性介紹）
.\full-pipeline.ps1 -InputVideo "raw.mp4" -Bilingual -Narrate

# 旁白 + 自訂語言 + 指定發音人
.\full-pipeline.ps1 -InputVideo "raw.mp4" -Bilingual -Narrate -NarrateLang en -NarrateVoice en-US-AriaNeural

# 自訂旁白稿
.\full-pipeline.ps1 -InputVideo "raw.mp4" -Narrate -NarrateScript "D:\scripts\narration.txt"

# 完整功能：雙語字幕 + 黑底 + 旁白 + BGM
.\full-pipeline.ps1 -InputVideo "raw.mp4" -Bilingual -AssFormat -SubBg black -Narrate -NarrateLang zh-TW -BgmFile "D:\music\bgm.mp3"
```

## Pipeline Verification

在執行完整產線後，建議執行以下驗證：

```powershell
# 使用驗證腳本
.\scripts\validate.ps1 -VideoPath "D:\output\final.mp4" -SrtPath "D:\output\subtitles.srt" -OutputPath "D:\output\final.mp4"

# 快速檢查
Write-Host "Duration comparison:"
Write-Host "  Input: $((ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 raw.mp4))s"
Write-Host "  Output: $((ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 final.mp4))s"
```

## Quality Checklist

- [ ] 影片可正常播放
- [ ] 影音同步無延遲
- [ ] 字幕顯示正確，時間軸對齊
- [ ] 雙語字幕：中文在上、英文在下，順序正確
- [ ] 動態字級縮放：以 1080p 為基準（zh=22px / en=16px），自動依影片高度調整
- [ ] 字型選擇：Noto Sans TC（繁體中文）、Arial（英文）
- [ ] 背景模式正確：`SubBg=black` 時黑底僅包覆文字；`SubBg=none` 時背景透明
- [ ] 背景音樂音量適中，不蓋過人聲
- [ ] 跳剪段落自然流暢
- [ ] 輸出檔案大小合理
- [ ] 編碼格式與目標平台相容

## Troubleshooting

| 問題 | 可能原因 | 解決方案 |
|------|---------|---------|
| 產線中途失敗 | 檔案不存在 | 檢查路徑和權限 |
| 字幕時間軸偏移 | Silence removal 改變了時間軸 | 先燒錄字幕再自動編輯，或使用 auto-editor 的 subtitle-aware 模式 |
| 雙語字幕錯位 | 中文與英文時間軸不一致 | 先以中文時間軸為主，使用腳本對齊；檢查 Whisper 的 zh/en 輸出 |
| 中文顯示方塊 | 缺少 CJK 字型 | 安裝 Noto Sans TC 字型（Google Fonts，開源免費可商用） |
| ASS 中文/英文大小不變 | ASS 樣式名稱錯誤或格式使用 SRT | 確認使用 `ass=` filter 而非 `subtitles=` |
| BGM 音量過大/過小 | volume 設定不當 | 調整 `volume=0.3` 數值 |
| 影片長度異常 | 自動編輯誤判 | 調整 silence threshold 參數 |
