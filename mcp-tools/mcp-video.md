# MCP Tools — mcp-video

## Overview

mcp-video 是一個開源的 MCP（Model Context Protocol）伺服器，
為 AI Agent 提供 80+ 結構化的影片編輯工具。
基於 FFmpeg，支援剪輯、字幕、音訊、特效、AI 功能等。

**原始碼**：https://github.com/KyaniteLabs/mcp-video
**文件**：https://kyanitelabs.github.io/mcp-video/
**PyPI**：`pip install mcp-video`

## Why mcp-video

| 特性 | mcp-video | 純 FFmpeg | 雲端 API |
|------|-----------|-----------|---------|
| 成本 | ✅ 免費、本機 | ✅ 免費 | ❌ $0.28-$2.50/次 |
| 隱私 | ✅ 100% 本機 | ✅ 100% 本機 | ❌ 上傳雲端 |
| 錯誤處理 | ✅ 結構化 + 自動修復 | ❌ 模糊的 stderr | ✅ API schema |
| 驗證 | ✅ 執行前驗證 | ❌ 僅執行時 | ✅ API schema |
| Agent 探索 | ✅ 80+ 自說明工具 | ❌ 需記憶 flag | ❌ 需閱讀文件 |
| 測試覆蓋 | ✅ 858 測試 | ❌ 無 | 供應商負責 |

## Installation

### 需求
- Python 3.11+
- FFmpeg（在 PATH 中）

### pip 安裝

```powershell
pip install mcp-video
```

### 驗證安裝

```powershell
# CLI 測試
mcp-video trim input.mp4 -s 0:30 -d 15 -o clip.mp4

# Python Client 測試
python -c "from mcp_video import Client; c=Client(); print('mcp-video ready')"
```

## MCP Configuration

### Claude Desktop

在 `claude_desktop_config.json` 中加入：

```json
{
  "mcpServers": {
    "mcp-video": {
      "command": "uvx",
      "args": ["mcp-video"]
    }
  }
}
```

### OpenCode / Codex

在 `opencode.json` 或 `~/.config/opencode/opencode.json` 中加入：

```json
{
  "mcpServers": {
    "mcp-video": {
      "command": "uvx",
      "args": ["mcp-video"]
    }
  }
}
```

## Tool Categories

mcp-video 提供 9 大類別共 80+ 工具：

| 類別 | 工具數量 | 用途 |
|------|---------|------|
| ✂️ 核心編輯 | 10 | Trim, merge, crop, rotate, resize, speed, fade |
| 🎨 濾鏡 | 8 | Blur, sharpen, grayscale, sepia, vignette |
| ✨ 特效 | 5 | Glitch, pixelate, scanlines, noise, glow |
| 🎬 轉場 | 3 | Glitch transition, pixelate, morph |
| 🎵 音訊 | 7 | Normalize, reverb, compress, pitch, noise reduction |
| 🤖 AI 功能 | 10 | Whisper 轉錄、場景偵測、人聲分離、AI 放大 |
| 📐 佈局 | 8 | Grid, PiP, split-screen, animated text |
| 📁 媒體分析 | 10 | Codec info, resolution, duration, quality check |
| ⚙️ 後處理 | 20+ | Format conversion, compression, validation |

## CLI Examples

### 核心編輯

```powershell
# 裁剪
mcp-video trim input.mp4 -s 1:30 -d 30 -o clip.mp4

# 合併
mcp-video merge clip1.mp4 clip2.mp4 clip3.mp4 -o combined.mp4

# 裁切
mcp-video crop input.mp4 -w 1280 -h 720 -x 0 -y 0 -o cropped.mp4

# 縮放
mcp-video resize input.mp4 -w 1920 -h 1080 -o hd.mp4

# 速度
mcp-video speed input.mp4 -f 2.0 -o fast.mp4

# 轉換
mcp-video convert input.mp4 -f webm -o output.webm
```

### 字幕

```powershell
# 加入字幕
mcp-video add-subtitles input.mp4 -s captions.srt -o subtitled.mp4

# 樣式化字幕
mcp-video add-subtitles input.mp4 -s captions.srt --font-size 24 --color white --outline black -o styled.mp4
```

### 音訊

```powershell
# 加入 BGM
mcp-video add-audio input.mp4 -a bgm.mp3 --volume 0.3 -o with_bgm.mp4

# 替換音訊
mcp-video replace-audio input.mp4 -a new_audio.mp3 -o replaced.mp4

# 提取音訊
mcp-video extract-audio input.mp4 -o audio.mp3
```

### AI 功能

```powershell
# Whisper 轉錄
mcp-video transcribe input.mp4 --model small --format srt

# 場景偵測
mcp-video detect-scenes input.mp4 --threshold 0.3

# 人聲分離
mcp-video separate-stems input.mp4 --output-dir stems/
```

### 特效與濾鏡

```powershell
# 黑白濾鏡
mcp-video filter input.mp4 -t grayscale -o bw.mp4

# 模糊
mcp-video filter input.mp4 -t blur --sigma 5 -o blurred.mp4

# 加入文字
mcp-video add-text input.mp4 "Hello World" -p center --size 48 -o text.mp4
```

## Python Client 範例

```python
from mcp_video import Client

client = Client()

# 完整工作流程
# 1. 裁剪
trimmed = client.trim("input.mp4", start="1:30", duration="30", output="trimmed.mp4")
print(f"Trimmed: {trimmed['duration']}s @ {trimmed['resolution']}")

# 2. 轉錄
client.transcribe("trimmed.mp4", model="small", format="srt")

# 3. 加入 BGM
mixed = client.add_audio("trimmed.mp4", audio="bgm.mp3", volume=0.3, output="mixed.mp4")

# 4. 輸出結果
print(f"Final output: {mixed['output_path']}")

# 錯誤處理
try:
    result = client.trim("nonexistent.mp4", start=0, duration=10)
except Exception as e:
    print(f"Error: {e}")
    print("Suggestion: Check if input file exists and is a valid video.")
```

## Agent Workflow 範例

當 AI Agent 需要處理影片時，可以使用以下自然語言請求透過 mcp-video 執行：

1. "Trim video.mp4 from 1:30 to 2:45"
2. "Convert input.mp4 to WebM format"
3. "Add subtitles.srt to video.mp4 with white text and black outline"
4. "Speed up video.mp4 by 2x"
5. "Merge clip1.mp4 and clip2.mp4"
6. "Extract audio from video.mp4 as MP3"
7. "Add bgm.mp3 as background music at 30% volume"
8. "Transcribe video.mp4 and generate SRT subtitles"

## Troubleshooting

| 問題 | 解決方案 |
|------|---------|
| `mcp-video: command not found` | 確認 `pip install mcp-video` 成功，且 Python Scripts 目錄在 PATH 中 |
| FFmpeg 相關錯誤 | 確認 `ffmpeg -version` 可正常執行 |
| GPU 加速問題 | 確認 FFmpeg 有編譯相應的 GPU 支援 |
| MCP 連接失敗 | 檢查 `uvx` 是否安裝，嘗試 `npx mcp-video` |
