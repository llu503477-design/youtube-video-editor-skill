# AI Subtitles — FFmpeg 8.0 Native Whisper Filter

## Overview

FFmpeg 8.0+ 新增了原生 Whisper filter，可在單一 FFmpeg 命令中完成語音轉文字。
無需安裝 Python Whisper 或額外工具，只需 FFmpeg 8.0+ 和一個 GGML 模型檔案。

## Requirements

- FFmpeg 8.0+（啟用 Whisper 支援）
- Whisper GGML 模型檔案（與 whisper.cpp 相容）

### Check FFmpeg Whisper Support

```powershell
# 確認 FFmpeg 版本
ffmpeg -version

# 確認 Whisper filter 可用
ffmpeg -filters | findstr whisper
```

如果沒有 Whisper filter，需要自行編譯 FFmpeg：
```powershell
# Windows: 使用 BtbN 的 FFmpeg-Builds
# 下載支援 whisper 的 build
```

### Download GGML Model

從 HuggingFace 下載 GGML 格式的 Whisper 模型：
```powershell
# 建立模型目錄
mkdir -p ~/whisper-models

# 下載 medium 模型（推薦平衡選擇）
curl -L -o ~/whisper-models/ggml-medium.bin `
    https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin

# 或下載 turbo 模型（最快準確度平衡）
curl -L -o ~/whisper-models/ggml-large-v3-turbo.bin `
    https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
```

## Basic Usage

### 產生中文 SRT 字幕（預設）

```powershell
ffmpeg -i input.mp4 -af "whisper=model=ggml-medium.bin:language=zh:format=srt" -f null -
```

這會產生名為 `input.srt` 的繁體中文字幕檔案（與輸入影片同目錄）。

### 自訂輸出路徑

```powershell
ffmpeg -i input.mp4 -af "whisper=model=ggml-medium.bin:language=zh:format=srt:destination=output.srt" -f null -
```

### 單命令：中文轉錄 + 燒錄字幕

```powershell
ffmpeg -i input.mp4 -af "whisper=model=ggml-medium.bin:language=zh:format=srt" -vf "subtitles=input.srt" -c:v libx264 -crf 23 -c:a aac output.mp4
```

## Advanced Parameters

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `model` | (required) | GGML 模型路徑 |
| `language` | auto | 語言代碼（en, zh, ja 等） |
| `format` | srt | 輸出格式（srt/vtt/txt/json） |
| `destination` | 輸入檔名 | 輸出檔案路徑 |
| `queue` | 0 | 內部佇列大小（建議 30 用於串流） |
| `vad` | true | 語音活動偵測（減少靜音段落文字） |

### VAD（Voice Activity Detection）控制

```powershell
# 啟用 VAD（預設，建議開啟）
ffmpeg -i input.mp4 -af "whisper=model=ggml-medium.bin:vad=true:format=srt" -f null -

# 停用 VAD（可能產生更多靜音段落文字）
ffmpeg -i input.mp4 -af "whisper=model=ggml-medium.bin:vad=false:format=srt" -f null -
```

### GPU 加速

```powershell
# CUDA 加速（需要 FFmpeg 編譯時啟用 CUDA）
ffmpeg -hwaccel cuda -i input.mp4 -af "whisper=model=ggml-medium.bin:language=zh:format=srt" -f null -
```

## Full Pipeline Pipeline: Download → Transcribe (zh) → Burn Bilingual

```powershell
# Step 1: 下載 YouTube 影片
yt-dlp -f "bestvideo+bestaudio" --merge-output-format mp4 -o "video.%(ext)s" "URL"

# Step 2: 使用 FFmpeg 8.0 Whisper 中文轉錄
ffmpeg -i video.mp4 -af "whisper=model=ggml-medium.bin:language=zh:format=srt" -f null -

# Step 3: 燒錄中文字幕 + 加入 BGM
ffmpeg -i video.mp4 -i bgm.mp3 `
    -filter_complex "[1:a]volume=0.3[bgm];[0:a][bgm]amix=inputs=2:duration=shortest[aout]" `
    -vf "subtitles=video.srt:force_style='FontName=Noto Sans TC,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=50,BorderStyle=1'" `
    -map 0:v -map "[aout]" -c:v libx264 -crf 23 -c:a aac final.mp4
```

## Bilingual Pipeline (zh-TW + EN)

若需雙語字幕（FFmpeg 8.0+ 需搭配 Python 額外處理英文翻譯）：

```powershell
# Step 1: 中文轉錄
ffmpeg -i input.mp4 -af "whisper=model=ggml-medium.bin:language=zh:format=srt" -f null -
# 產生 input.srt（中文）

# Step 2: 提取音訊 + 使用 Python Whisper 產生英文翻譯
ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav
pwsh -File scripts/whisper-cli.ps1 audio.wav -Language zh -Task translate -OutputPrefix output/en/audio

# Step 3: 合併雙語字幕（使用 ASS 格式支援不同字級）
python scripts/generate_bilingual_ass.py input.srt audio.srt bilingual.ass

# Step 4: 燒錄雙語字幕（中文大、英文小）
ffmpeg -i input.mp4 -vf "ass=bilingual.ass" -c:v libx264 -crf 23 -c:a aac output.mp4
```

## Limitations

1. **FFmpeg 版本要求**：僅 FFmpeg 8.0+ 支援，且需啟用 Whisper 模組
2. **模型格式**：僅支援 GGML 格式（與 whisper.cpp 相容）
3. **GPU 支援**：需特定編譯選項才能啟用 GPU 加速
4. **語言自動偵測**：不如 Python Whisper 準確，建議手動指定語言
5. **無說話者標記**：相較 WhisperX 缺少 speaker diarization

## Comparison: FFmpeg Whisper vs Python Whisper

| 特性 | FFmpeg 8.0 Whisper | Python Whisper |
|------|-------------------|----------------|
| 安裝步驟 | 下載 FFmpeg + 模型 | pip install + 模型 |
| GPU 加速 | 需特定編譯 | CUDA 開箱即用 |
| 整合性 | 單一命令完成 | 需腳本串接 |
| 模型支援 | 僅 GGML 格式 | PyTorch + GGML |
| 說話者標記 | ❌ | ✅ (WhisperX) |
| 批次處理 | 需腳本包裝 | 內建 |


## Best Practices

1. **指定語言**：強烈建議手動指定 `language=zh` 以提升繁體中文準確度
2. **VAD 開啟**：預設啟用 VAD，可減少無語音段落的雜訊文字
3. **中型模型為佳**：medium 模型在速度/準確度間取得最佳平衡
4. **雙語限制**：FFmpeg 8.0 Whisper filter 不支援翻譯（`task=translate`），英文翻譯需使用 Python Whisper
5. **檢查輸出**：轉錄後務必抽查 SRT 內容的正確性，特別是中文繁體字元
