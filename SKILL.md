---
name: youtube-video-editor
description: 使用 FFmpeg、Auto-Editor 31、Whisper、qwentts.cpp、yt-dlp 與內附腳本完成 YouTube 或本機影片的剪裁、分割、合併、轉檔、壓縮、濾鏡、文字與浮水印、速度調整、縮圖、背景音樂混音、preview-first 靜音移除、自動跳剪、語音轉字幕、Qwen3-TTS 授權語音複製、繁體中文與英文雙語 SRT/ASS、字幕燒錄、旁白及批次產線。當使用者要求影片剪輯、自動影片處理、Auto-Editor、YouTube 下載、字幕或 captions、Whisper transcription、voice cloning、聲音複製、BGM/音軌混合、CapCut-like CLI、FFmpeg 指令或 mcp-video 工作流程時使用。
---

# YouTube Video Editor

使用可重現的 CLI 管線編輯影片。先保留原始檔，再以新路徑輸出；除非使用者明確允許，不覆寫既有檔案。

## 執行流程

1. 執行 `scripts/check-dependencies.ps1`，確認 FFmpeg 與 FFprobe；只有工作需要時才要求選用依賴。
2. 使用 FFprobe 檢查輸入串流、時長、解析度、幀率與音訊配置。
3. 依任務讀取下方唯一必要的參考文件，不要一次載入全部文件。
4. 優先使用參數陣列呼叫 CLI，正確處理含空白的路徑；避免以字串拼接 shell 命令。
5. 先以短片段驗證複雜 filter graph，再處理完整影片或批次。
6. 執行 `scripts/validate.ps1 -VideoPath <input> -SrtPath <optional.srt> -OutputPath <output>`，並以 FFprobe 與實際播放抽查結果。

內附腳本預設拒絕覆寫既有輸出；只有使用者明確同意時才傳入 PowerShell 的 `-Force` 或 Python CLI 的 `--force`。`narrate.py` 預設任一 TTS 段失敗就停止；只有使用者接受缺段與靜音 placeholder 時才使用 `--allow-partial`。

## 資源導覽

- 剪裁、合併、裁切、縮放與轉檔：讀取 [ffmpeg-core/basic-editing.md](ffmpeg-core/basic-editing.md)。
- 濾鏡、文字與浮水印：讀取 [ffmpeg-core/filters-effects.md](ffmpeg-core/filters-effects.md)。
- 背景音樂、混音與 ducking：讀取 [ffmpeg-core/audio-bgm.md](ffmpeg-core/audio-bgm.md)。
- SRT/ASS、雙語字幕與燒錄：讀取 [ffmpeg-core/subtitles.md](ffmpeg-core/subtitles.md)。
- Whisper 字幕產線：讀取 [ai-subtitles/whisper-pipeline.md](ai-subtitles/whisper-pipeline.md)；只有 FFmpeg 確實提供 `whisper` filter 時才讀取 [ai-subtitles/ffmpeg8-whisper.md](ai-subtitles/ffmpeg8-whisper.md)。
- Windows 全域 whisper.cpp 安裝：執行 `scripts/install-whisper-cpp.ps1`；轉錄時優先執行 `scripts/whisper-cli.ps1`，它預設使用 multilingual `large-v3-turbo` 並支援影片自動抽取音訊。
- Qwen3-TTS 語音複製：讀取 [ai-subtitles/qwentts-voice-cloning.md](ai-subtitles/qwentts-voice-cloning.md)；安裝執行 `scripts/install-qwentts-cpp.ps1`，合成優先使用全域 `qwen-voice-clone` 或 `scripts/qwen-voice-clone.ps1`。
- 旁白與 Edge-TTS：讀取 [ai-subtitles/narration.md](ai-subtitles/narration.md)。
- 靜音移除或跳剪：先讀取 [auto-editing/silence-removal.md](auto-editing/silence-removal.md)；需要策略選擇時再讀取 [auto-editing/jump-cut.md](auto-editing/jump-cut.md)。Windows 安裝執行 `scripts/install-auto-editor.ps1`，一般操作優先使用全域 `auto-edit` 或 `scripts/auto-edit.ps1`，先 `Preview` 再 `Render`。
- YouTube 下載：讀取 [youtube-download/yt-dlp.md](youtube-download/yt-dlp.md)，並遵守來源授權與平台規範。
- 批次或完整產線：讀取 [workflows/batch-processing.md](workflows/batch-processing.md) 或 [workflows/full-pipeline.md](workflows/full-pipeline.md)。
- 常用命令列剪輯：執行 `scripts/capcut.ps1`，並在需要時讀取 [workflows/capcut-cli.md](workflows/capcut-cli.md)。
- MCP 編輯：只有使用者要求 MCP 時才讀取 [mcp-tools/mcp-video.md](mcp-tools/mcp-video.md)。
- 縮圖：執行 `scripts/thumbnail.py`。

## Auto-Editor 全域執行基線

Windows 使用官方 Auto-Editor `31.3.2` binary，不使用已停止發布 CLI 的 pip。
安裝器驗證 GitHub release SHA-256、安裝到 `%LOCALAPPDATA%\auto-editor\bin`、
加入使用者 PATH，並設定 `AUTO_EDITOR_EXE`：
```powershell
pwsh -File scripts/install-auto-editor.ps1
auto-editor --version
auto-edit -?
```
一般任務先預覽；統計合理後才用相同 profile 輸出：
```powershell
auto-edit -InputPath input.mp4 -Profile Balanced -Mode Preview
auto-edit -InputPath input.mp4 -OutputPath output/edited.mp4 `
  -Profile Balanced -Mode Render
```
wrapper 預設拒絕覆寫；明確使用 `-Force` 時會先把既有輸出移到時間戳備份。
自動剪輯會改變時間軸，因此預設在 Whisper、外部字幕、章節、旁白與 overlay
之前執行。完成後至少抽查五個剪輯點。

## whisper.cpp 全域執行基線

Windows 工作優先使用已安裝於目前使用者環境的官方 whisper.cpp，不要再預設
呼叫 Python `whisper`：

- 版本：`whisper.cpp 1.9.1`
- 主要後端：CUDA 12.4 x64；已驗證 NVIDIA RTX 3070 Ti 可載入
- 回退後端：CPU x64
- 預設模型：multilingual `large-v3-turbo`，非量化版
- 全域 CLI：`%LOCALAPPDATA%\whisper.cpp\bin\whisper-cli.exe`
- CPU CLI：`%LOCALAPPDATA%\whisper.cpp\cpu-bin\whisper-cli.exe`
- 模型：`%LOCALAPPDATA%\whisper.cpp\models\ggml-large-v3-turbo.bin`
- 使用者環境變數：`WHISPER_CPP_EXE`、`WHISPER_CPP_MODEL`

全域 PATH 或環境變數剛完成安裝時，必須開啟新終端。先執行：

```powershell
whisper-cli --version
Test-Path $env:WHISPER_CPP_MODEL
```

直接使用全域 CLI 時必須明確傳入模型：

```powershell
whisper-cli -m $env:WHISPER_CPP_MODEL -f audio.wav -l zh --output-srt -of output/audio
```

影片或一般技能工作優先使用 wrapper；它會將非原生音訊輸入抽成 16 kHz mono
WAV、預設使用 `large-v3-turbo`、建立指定輸出目錄，並拒絕意外覆寫：

```powershell
# 中文轉錄
pwsh -File scripts/whisper-cli.ps1 input.mp4 -Language zh -OutputPrefix output/input

# 中文語音翻譯成英文字幕
pwsh -File scripts/whisper-cli.ps1 input.mp4 -Language zh -Task translate -OutputPrefix output/input_en

# CUDA 不可用時改走 CPU
pwsh -File scripts/whisper-cli.ps1 input.mp4 -Language zh -Cpu -OutputPrefix output/input_cpu
```

缺少 runtime 或模型時，執行 `pwsh -File scripts/install-whisper-cpp.ps1`。安裝器固定
使用官方 `v1.9.1` CUDA/CPU 發行資產並檢查 SHA-256；詳細安裝位置、官方雜湊及
驗收方式見 [ai-subtitles/whisper-pipeline.md](ai-subtitles/whisper-pipeline.md)。

## qwentts.cpp 語音複製基線

需要複製參考聲音產生影片旁白時，優先使用目前 Windows 使用者的全域
`qwen-voice-clone` wrapper：

```powershell
qwen-voice-clone `
  -TextFile narration.txt `
  -ReferenceWav reference.wav `
  -ReferenceTextFile reference.txt `
  -Language Chinese `
  -OutputPath output/narration.wav
```

- 預設模型為 1.7B Base Q8_0，codec 為 12 Hz Q8_0。
- 全域 CLI 位於 `%LOCALAPPDATA%\qwentts.cpp\bin`，模型位於
  `%LOCALAPPDATA%\qwentts.cpp\models`；使用者環境變數為
  `QWENTTS_CPP_EXE`、`QWENTTS_CPP_MODEL`、`QWENTTS_CPP_CODEC`。
- `ReferenceText` 必須是參考音訊的精確逐字稿，才能啟用完整 ICL clone。
- wrapper 保留參考原檔、自動建立暫時的 24 kHz mono WAV，並拒絕意外覆寫。
- 只有已取得聲音權利人授權時才執行 voice cloning；對外發布時依情境標示 AI 合成。
- CUDA 失敗可改用 `-Cpu`，但必須如實記錄實際 backend。
- 完整安裝、裸 CLI、預編碼 voice reference、雜湊與驗收方式見
  [ai-subtitles/qwentts-voice-cloning.md](ai-subtitles/qwentts-voice-cloning.md)。
- 本機已以 RTX 3070 Ti 完成繁中 ICL smoke：輸出 6.48 秒、24 kHz mono PCM16，
  日誌確認 `CUDA0`；效能與音色相似度仍須針對正式參考音訊重新驗收。

---

## 2. Core Philosophy

### 2.1 FFmpeg 是核心引擎

FFmpeg 是所有影片操作的核心。本技能的所有工作流程都建立在 FFmpeg 的基礎上。
理解 FFmpeg 的 filter graph 模型是進階操作的關鍵：

```
Input → Decode → Filters → Encode → Output
                   │
            [filter_complex]
           ┌────────┴────────┐
       裁剪/縮放          字幕疊加
       濾鏡鏈             音訊混合
```

### 2.2 雙語字幕策略（預設 zh-TW + English）

本技能預設採用 **繁體中文為主、英文為輔** 的雙語字幕策略：

- **預設語言**：繁體中文（zh-TW）為主體，英文（en）為次要
- **字體大小**：中文字幕採用較大字級（如 24px），英文採用較小字級（如 18px）
- **上下行配置**：中文顯示於上方（或第一行），英文顯示於下方（或第二行）
- **實現方式**：使用 ASS 格式定義兩種文字樣式，或透過 Python 腳本合併雙語 SRT

### 2.3 字幕生成的兩階段策略

字幕處理分為兩階段：
1. **生成階段**：使用 Whisper 模型將語音轉為文字，輸出 SRT/ASS 格式（預設語言 `zh`）
2. **燒錄階段**：使用 FFmpeg `subtitles` / `ass` filter 將字幕嵌入影片像素，採雙語 ASS 樣式

FFmpeg 8.0+ 支援原生 Whisper filter，可在單一命令中完成兩階段操作。

### 2.4 無損 vs 有損操作

| 操作類型 | 命令標誌 | 品質影響 | 速度 |
|---------|---------|---------|------|
| 直接複製 | `-c:v copy -c:a copy` | 無損 | 最快 |
| 僅重新編碼音訊 | `-c:v copy -c:a aac` | 影片無損 | 快 |
| 完整重新編碼 | `-c:v libx264 -crf 23` | 有損（可調） | 慢 |
| GPU 加速編碼 | `-c:v h264_nvenc` | 有損（較低壓縮率） | 快 |

### 2.5 自動化優先

本技能優先使用 CLI 工具和腳本實現自動化。所有操作都設計為可批次執行、
可重現、可整合到 CI/CD 管線中。

### 2.6 MCP 工具整合

mcp-video 提供 80+ 結構化影片編輯工具，讓 AI Agent 能透過自然語言操作影片。
本技能涵蓋 mcp-video 的安裝、配置與使用指南。

---

## 3. Ecosystem Matrix

| 類別 | 工具 | 用途 | 平台 |
|------|------|------|------|
| **核心引擎** | FFmpeg | 影片/音訊編解碼、濾鏡、串流操作 | Windows/macOS/Linux |
| **字幕生成** | OpenAI Whisper | AI 語音轉文字 | Python (pip) |
| **字幕生成** | whisper.cpp | 高效能 C++ 語音辨識 | Windows/macOS/Linux |
| **字幕生成** | faster-whisper | 4x 加速 Whisper 推論 | Python (pip) |
| **自動剪輯** | Auto-Editor 31 official binary + `auto-edit` | 預覽、靜音/動態分析、跳剪與 NLE 匯出 | Windows/macOS/Linux |
| **影片下載** | yt-dlp | YouTube 及 1000+ 網站下載 | Windows/macOS/Linux |
| **MCP 工具** | mcp-video | 80+ 結構化影片編輯 MCP 工具 | Python 3.11+ |
| **音訊處理** | FFmpeg amix | 多軌音訊混合 | 內建於 FFmpeg |
| **格式轉換** | FFmpeg | 支援所有主流格式 | 內建於 FFmpeg |
| **機器翻譯** | HuggingFace MarianMT | 本地離線 EN→zh-CN 翻譯 | Python (transformers) |
| **繁簡轉換** | OpenCC | zh-CN ↔ zh-TW 高精度轉換 | Python (pip) |
| **雙語整合** | generate_bilingual_ass.py | 合併中英文 SRT 為雙語 ASS（動態字級縮放） | Python 3.8+ |

---

## 4. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Input Sources                         │
│  YouTube (yt-dlp) │ Local Files │ Screen Recording      │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  Pre-processing                          │
│  Trim / Crop / Resize / Speed / Format Convert          │
│  └─ FFmpeg filter graphs, stream copy or re-encode      │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Auto Editing (Optional)                     │
│  auto-edit: preview → profile → render / NLE export      │
│  audio, motion, subtitle or boolean-composed analysis     │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Subtitle Generation                         │
│  Whisper(zh) → audio extraction → transcription → SRT   │
│  Whisper(translate) → English SRT                       │
│  Merge → bilingual SRT (zh-TW main + EN secondary)      │
│  FFmpeg 8.0+: native whisper filter for single-step     │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Narration Generation (Optional)              │
│  narrate.py: subtitles → narration script per segment    │
│  Edge-TTS: TTS in zh-TW / en / ja / ko...               │
│  --mode intro: stage-by-stage guide                     │
│  --mode full/summary: read-aloud or short summary       │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Audio Mixing                                │
│  amix: mix original audio + BGM                         │
│  sidechaincompress: auto-duck when narration plays      │
│  acrossfade: smooth transitions between segments        │
│  volume: adjust individual track levels                 │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│              CapCut-like CLI (capcut.ps1)                │
│  trim / split / merge / text / audio / speed / subtitle │
│  All operations fall back to pure FFmpeg                │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Output & Publishing                        │
│  subtitle burn: bilingual ASS / SRT                     │
│  thumbnail.py: YouTube thumbnail with large bold text   │
│  capcut export: encode final output                     │
│  ffmpeg: direct encode                                  │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│              Subtitle Burning                            │
│  subtitles filter: burn SRT/ASS into video frames       │
│  force_style: customize font, color, position           │
│  -SubBg none:   transparent, outline+shadow             │
│  -SubBg black:  black box behind text (default)         │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  Output                                  │
│  MP4 / WebM / MKV / Custom format                       │
│  Single file or batch output                            │
└─────────────────────────────────────────────────────────┘
```

---

## 5. Quick Reference: Common FFmpeg Commands

### Video Trimming
```powershell
ffmpeg -i input.mp4 -ss 00:01:30 -t 00:00:30 -c:v copy -c:a copy output.mp4
```

### Burn Bilingual Subtitles with ASS (zh-TW + EN, default: outline+shadow)
```powershell
# 使用 ASS 雙語字幕（預設不透明背景 BorderStyle=1：外框+陰影）
# 中文 Noto Sans TC FontSize=22，英文 Arial FontSize=16（1080p 基準，動態縮放）
# 自動偵測影片高度計算字級（--scale 或 --video-height）
ffmpeg -i input.mp4 -vf "ass=bilingual.ass" -c:v libx264 -crf 23 -c:a aac output.mp4

# 黑底模式（BorderStyle=4）— 遮蓋原始影片字幕
python scripts/generate_bilingual_ass.py zh.srt en.srt bilingual.ass --background black --video-height 720
ffmpeg -i input.mp4 -vf "ass=bilingual.ass" -c:v libx264 -crf 23 -c:a aac output.mp4
```

### Generate Bilingual SRT (zh-TW + EN merged)
```powershell
# Whisper 中文轉錄 + 英文翻譯 → 合併雙語 SRT → 燒錄
pwsh -File scripts/whisper-cli.ps1 audio.wav -Language zh -Task transcribe -OutputPrefix output/zh/audio
pwsh -File scripts/whisper-cli.ps1 audio.wav -Language zh -Task translate -OutputPrefix output/en/audio
python scripts/merge_bilingual_srt.py output/zh/audio.srt output/en/audio.srt bilingual.srt
ffmpeg -i input.mp4 -vf "subtitles=bilingual.srt:force_style='FontName=Noto Sans TC,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=50,BorderStyle=1'"
       -c:v libx264 -crf 23 -c:a aac output.mp4
```

### Add Background Music (amix)
```powershell
ffmpeg -i input.mp4 -i bgm.mp3 -filter_complex "[0:a][1:a]amix=inputs=2:duration=shortest:dropout_transition=2[aout]"
       -map 0:v:0 -map "[aout]" -c:v copy -c:a aac -b:a 192k output.mp4
```

### Auto-Editor Silence Removal
```powershell
# 先預覽統計，再以相同 profile 輸出
auto-edit -InputPath input.mp4 -Profile Balanced -Mode Preview
auto-edit -InputPath input.mp4 -OutputPath output.mp4 -Profile Balanced -Mode Render
```

### Generate Video Narration from Subtitles (TTS Voiceover)
```powershell
# 從字幕產生階段性旁白（繁體中文，intro 模式）
python scripts/narrate.py --subs bilingual.srt --lang zh-TW --mode intro --output narration.wav

# 英文旁白（用於國際化）
python scripts/narrate.py --subs bilingual.srt --lang en --voice en-US-AriaNeural --output narration_en.wav

# 自訂旁白稿
python scripts/narrate.py --script narration_script.txt --lang zh-TW --output narration.wav

# 旁白 + 對齊時間軸的字幕輸出（旁白說什麼，字幕就顯示什麼）
python scripts/narrate.py --subs bilingual.srt --lang zh-TW --mode intro --output narration.wav --output-subs narration.srt

# 混音：旁白 + 原始音訊（auto-ducking）
ffmpeg -i input.mp4 -i narration.wav `
    -filter_complex "[1:a][0:a]sidechaincompress=level_in=1:threshold=0.015:ratio=10:attack=100:release=500[ducked];[ducked][1:a]amix=inputs=2:duration=first[aout]" `
    -map 0:v -map "[aout]" -c:v copy -c:a aac output.mp4
```

### Generate Bilingual Subtitles with Whisper (zh-TW + EN)
```powershell
# Step 1: Audio extraction
ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav
# Step 2: Transcribe Chinese (zh)
pwsh -File scripts/whisper-cli.ps1 audio.wav -Language zh -Task transcribe -OutputPrefix output/zh/audio
# Step 3: Translate to English
pwsh -File scripts/whisper-cli.ps1 audio.wav -Language zh -Task translate -OutputPrefix output/en/audio
# Step 4: Merge bilingual SRT (Chinese main, English sub)
python scripts/merge_bilingual_srt.py output/zh/audio.srt output/en/audio.srt bilingual.srt
# Step 5: Burn bilingual subtitles (Chinese larger, English smaller via ASS)
ffmpeg -i input.mp4 -vf "subtitles=bilingual.srt" -c:v libx264 -crf 23 -c:a copy output.mp4
```

### Full Bilingual Pipeline: English Audio → zh-TW + EN Subtitles

> ⚠️ **v1.2 起 deprecated**：generate_bilingual_from_en.py 不再維護。
> 改用兩階段 Whisper 管線（更簡單、更準確）：

```powershell
# Step 1: 中文轉錄
pwsh -File scripts/whisper-cli.ps1 audio.wav -Language zh -Task transcribe -OutputPrefix output/zh/audio
# Step 2: 英文翻譯（使用獨立目錄，避免覆寫中文 SRT）
pwsh -File scripts/whisper-cli.ps1 audio.wav -Language zh -Task translate -OutputPrefix output/en/audio
# Step 3: 合併為雙語 ASS（自動偵測影片高度動態縮放字級）
python scripts/generate_bilingual_ass.py output/zh/audio.srt output/en/audio.srt bilingual.ass --background none --video-height (ffprobe -v error -select_streams v:0 -show_entries stream=height -of default=noprint_wrappers=1:nokey=1 input.mp4)
# Step 4: 燒錄雙語字幕（Noto Sans TC 開源字型，動態字級）
ffmpeg -i input.mp4 -vf "ass=bilingual.ass" -c:v libx264 -crf 23 -c:a aac output.mp4
```

### YouTube Download with yt-dlp
```powershell
yt-dlp -f "bestvideo+bestaudio" --merge-output-format mp4 "URL"
```

### Generate YouTube Thumbnail (eye-catching large text overlay)
```powershell
# 從圖片產生縮圖（1280×720，大字發光標題）
python scripts/thumbnail.py --bg background.jpg --title "重磅消息" --subtitle "Breaking News" --output thumb.jpg

# 從影片擷取畫面做背景
python scripts/thumbnail.py --video input.mp4 --time 10 --title "超強教學" --title-size 120 --glow "#FF4400" --output thumb.jpg
```

### CapCut-like CLI (FFmpeg backend)
```powershell
# 剪輯片段
.\scripts\capcut.ps1 trim input.mp4 -start 00:30 -end 01:30 -o clip.mp4

# 分割影片
.\scripts\capcut.ps1 split input.mp4 -at 00:45

# 合併多段
.\scripts\capcut.ps1 merge "part1.mp4,part2.mp4" -o combined.mp4

# 加入文字標題
.\scripts\capcut.ps1 text input.mp4 -t "超強解說" -o titled.mp4

# 加入背景音樂
.\scripts\capcut.ps1 audio input.mp4 -bgm bgm.mp3 -o with_bgm.mp4

# 調整速度
.\scripts\capcut.ps1 speed input.mp4 -rate 2.0 -o fast.mp4

# 燒錄字幕
.\scripts\capcut.ps1 subtitle input.mp4 -srt subtitle.srt -o subbed.mp4

# 顯示影片資訊
.\scripts\capcut.ps1 info input.mp4
```

---

## 6. Quality Gates

### Pre-flight Checks
- [ ] FFmpeg 已安裝並在 PATH 中 (`ffmpeg -version`)
- [ ] Auto-Editor 任務已確認 `auto-editor --version` 與 `auto-edit -?`
- [ ] whisper.cpp 已安裝並在 PATH 中 (`whisper-cli --version`)
- [ ] `WHISPER_CPP_MODEL` 指向可讀取的 `ggml-large-v3-turbo.bin`
- [ ] 語音複製任務已確認授權，且 `qwen-tts --help`、模型與 codec 均可用
- [ ] 語音複製參考 WAV 清晰，`ReferenceText` 與實際內容逐字一致
- [ ] 輸入檔案存在且可讀取
- [ ] 輸出目錄有足夠的磁碟空間
- [ ] 字幕檔案格式正確（SRT 使用 UTF-8 編碼）
- [ ] BGM 檔案格式受支援

### Post-flight Verification
- [ ] 輸出檔案存在且大小合理
- [ ] Auto-Editor 已先 Preview，且人工抽查至少五個剪輯點
- [ ] whisper.cpp 結束碼為 0，且實際建立要求的 SRT/VTT/TXT/JSON
- [ ] CUDA 任務日誌出現 `loaded CUDA backend`；失敗時明確改用 `-Cpu`
- [ ] Qwen3-TTS 輸出是可解碼的 24 kHz mono WAV，並已實際聆聽抽查
- [ ] 影片長度與預期一致
- [ ] 雙語字幕顯示正確（中文主體在上、英文在下、時間軸對齊）
- [ ] 中文字級較大、英文字級較小（ASS 雙樣式檢查）
- [ ] 音訊混合比例恰當（BGM 不蓋過人聲）
- [ ] 自動剪輯未移除重要內容

### Output Quality Metrics
| 指標 | 目標值 | 檢查方式 |
|------|--------|---------|
| 輸出檔案可播放 | 是 | `ffprobe output.mp4` |
| 影音同步 | ±1 影格 | 視覺檢查 |
| 字幕時間準確度 | ±0.5s | 抽查 3 個時間點 |
| 雙語字幕對齊 | 中文/英文時間一致 | 檢查兩條 SRT 時間戳差異 < 0.3s |
| 字型大小比例 | 中文 > 英文 4~6px | 視覺檢查 ASS 樣式定義 |
| 字幕背景模式 | 黑底僅包覆文字，非全螢幕寬 | 檢查 BorderStyle=4 的渲染範圍 |
| 無黑底模式 | 背景完全透明，不遮蓋畫面 | 檢查 BorderStyle=1 + Outline/Shadow |
| 旁白時間同步 | 旁白與對應字幕段落同時出現 | 聽覺檢查 ±0.5s |
| Ducking 效果 | 旁白播放時原始音訊降至 ~30% | 波形檢查旁白區間的音量降低 |
| BGM 音量比例 | 人聲 -6dB ~ -3dB | 聽覺 + 波形檢查 |

---

## 7. Violation Rules

### Never（禁止）
- ❌ 不要使用未驗證的字幕檔案（可能包含亂碼或時間軸偏移）
- ❌ 不要在未備份原始影片的情況下直接覆蓋輸出
- ❌ 不要對串流使用 `-c copy` 時又疊加需要重新編碼的濾鏡
- ❌ 不要在未確認版權的情況下使用受版權保護的 BGM
- ❌ 不要使用 `ffmpeg` 的 `-y` 旗標而意外覆蓋重要檔案

### Warn（警告）
- ⚠️ GPU 加速編碼（NVENC/AMF）的壓縮率低於軟體編碼
- ⚠️ Whisper 大模型需要大量 VRAM（large-v3 約需 10GB）
- ⚠️ 批次處理時注意磁碟空間和 CPU/GPU 溫度
- ⚠️ 自動剪輯可能誤刪有意的暫停/留白
- ⚠️ SRT 字幕合併時 FFmpeg 可能無聲失敗

### Always（務必）
- ✅ 大量操作前先用單一檔案測試管線
- ✅ 為輸出檔案使用明確的路徑和檔名
- ✅ 記錄使用的 FFmpeg 命令以便重現
- ✅ 字幕生成後抽查正確性
- ✅ 先以 `ffmpeg -filters` 確認本機版本真的提供 `whisper` filter，再採用原生 Whisper 管線

---

## 8. References

- [FFmpeg Official Documentation](https://ffmpeg.org/documentation.html)
- [FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html)
- [OpenAI Whisper](https://github.com/openai/whisper)
- [Whisper.cpp](https://github.com/ggml-org/whisper.cpp)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [Auto-Editor](https://github.com/WyattBlue/auto-editor)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [mcp-video](https://github.com/KyaniteLabs/mcp-video)
- [FFmpeg 8.0 Whisper Filter](https://ffmpeg.org/ffmpeg-filters.html#whisper)
- [FFmpeg Subtitles HowTo](https://trac.ffmpeg.org/wiki/HowToBurnSubtitlesIntoVideo)
- [Helsinki-NLP/opus-mt-en-zh (MarianMT)](https://huggingface.co/Helsinki-NLP/opus-mt-en-zh)
- [OpenCC (繁簡轉換)](https://github.com/BYVoid/OpenCC)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
