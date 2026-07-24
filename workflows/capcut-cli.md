# Workflow — CapCut-like CLI (FFmpeg Backend)

## Overview

內建類 CapCut 的命令列影片編輯工具，提供直覺的 `trim` / `split` / `merge` / `text` / `audio` / `speed` / `subtitle` / `export` 指令，
底層完全使用 **FFmpeg** 引擎，無需 GUI、無需額外依賴。

## Core Philosophy

```
capcut.ps1             ← 類 CapCut 的簡單 CLI
    │
    ├── trim           ← ffmpeg -ss -to -c:v libx264
    ├── split          ← ffmpeg -ss -to (分兩次)
    ├── merge          ← ffmpeg concat demuxer
    ├── text           ← ffmpeg drawtext filter
    ├── audio          ← ffmpeg amix + volume
    ├── speed          ← ffmpeg setpts + atempo
    ├── subtitle       ← ffmpeg subtitles filter
    ├── export         ← ffmpeg copy/re-encode
    └── info           ← ffprobe JSON
```

所有操作最終都轉譯為 FFmpeg 命令，確保：
- 完全相容原始 FFmpeg 技能生態
- 可直接取用 FFmpeg 的所有編解碼器與濾鏡
- 零外部依賴（僅需 FFmpeg）

## Installation

無需安裝 — `capcut.ps1` 內建於技能目錄 `scripts/` 中。

```powershell
# 確認 FFmpeg 可用
ffmpeg -version

# 執行 capcut
.\scripts\capcut.ps1 help
```

## Commands

### `help` — 顯示說明

```powershell
.\scripts\capcut.ps1 help
```

### `trim` — 剪輯片段

```powershell
# 從 30 秒到 1 分 30 秒
.\scripts\capcut.ps1 trim input.mp4 -start 00:30 -end 01:30 -o clip.mp4

# 從開頭到 45 秒
.\scripts\capcut.ps1 trim input.mp4 -end 00:45 -o first_half.mp4
```

| 參數 | 說明 |
|------|------|
| `-start` | 開始時間（SS 或 HH:MM:SS） |
| `-end` | 結束時間（SS 或 HH:MM:SS） |
| `-o` / `-Output` | 輸出檔案（預設：input_trim.mp4） |

### `split` — 分割影片

```powershell
# 在第 45 秒分割為兩段
.\scripts\capcut.ps1 split input.mp4 -at 00:45
# 輸出：input_part1.mp4, input_part2.mp4
```

| 參數 | 說明 |
|------|------|
| `-at` | 分割時間點（必填） |

### `merge` — 合併多段影片

```powershell
# 合併兩段影片（逗號分隔）
.\scripts\capcut.ps1 merge "part1.mp4,part2.mp4" -o merged.mp4

# 合併多段
.\scripts\capcut.ps1 merge "intro.mp4,main.mp4,outro.mp4" -o full.mp4
```

| 參數 | 說明 |
|------|------|
| Input | 逗號分隔的檔案路徑 |
| `-o` | 輸出檔案（預設：merged.mp4） |

> **注意**：合併使用 FFmpeg concat demuxer（不重新編碼），
> 若格式不相容會自動降級為重新編碼合併。

### `text` — 加入文字標題

```powershell
# 基本：底部文字（白色 + 黑色描邊 + 陰影）
.\scripts\capcut.ps1 text input.mp4 -t "超強解說" -o titled.mp4

# 自訂字型與大小
.\scripts\capcut.ps1 text input.mp4 -t "重磅消息" -FontSize 48 -o big_title.mp4
```

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `-t` / `-Text` | (必填) | 顯示文字 |
| `-FontSize` | `22` | 字級（px） |
| `-FontName` | `Noto Sans TC` | 字型名稱 |
| `-o` | input_texted.mp4 | 輸出檔案 |

### `audio` — 加入背景音樂

```powershell
# 加入 BGM（自動混音，BGM 音量 30%）
.\scripts\capcut.ps1 audio input.mp4 -bgm bgm.mp3 -o with_bgm.mp4
```

| 參數 | 說明 |
|------|------|
| `-bgm` | 背景音樂檔案 |

### `speed` — 調整速度

```powershell
# 2 倍快轉
.\scripts\capcut.ps1 speed input.mp4 -rate 2.0 -o fast.mp4

# 0.5 倍慢動作
.\scripts\capcut.ps1 speed input.mp4 -rate 0.5 -o slowmo.mp4
```

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `-rate` | `1.0` | 倍率（0.25–4.0 建議範圍） |

### `subtitle` — 燒錄字幕

```powershell
# 燒錄 SRT 字幕
.\scripts\capcut.ps1 subtitle input.mp4 -srt caption.srt -o subbed.mp4

# 自訂字型
.\scripts\capcut.ps1 subtitle input.mp4 -srt subs.srt -FontName "Noto Sans TC" -FontSize 28 -o subbed.mp4
```

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `-srt` | (必填) | SRT 字幕檔案 |
| `-FontSize` | `22` | 字級 |
| `-FontName` | `Noto Sans TC` | 字型 |

### `export` — 匯出最終影片

```powershell
# 重新編碼輸出（確保相容性）
.\scripts\capcut.ps1 export final_cut.mp4 -o published.mp4
```

### `info` — 顯示影片資訊

```powershell
.\scripts\capcut.ps1 info input.mp4
```

輸出範例：
```
  ═══════════════ Video Info ═══════════════
  File:       input.mp4
  Duration:   125.34s
  Bitrate:    2500 kbps
  Size:       38.2 MB
  ─ Video ─
    Codec:    h264
    Resol:    1920x1080
    FPS:      30/1
  ─ Audio ─
    Codec:    aac
    Sample:   48000 Hz
    Channel:  2
```

## Pipeline Integration

`capcut.ps1` 可直接與現有工作流程組合：

```powershell
# 完整產線：下載 → 修剪 → 字幕 → BGM → 匯出
yt-dlp -f "bestvideo+bestaudio" "URL" -o raw.mp4
.\scripts\capcut.ps1 trim raw.mp4 -start 00:30 -end 05:00 -o trimmed.mp4
.\scripts\capcut.ps1 subtitle trimmed.mp4 -srt bilingual.srt -o subbed.mp4
.\scripts\capcut.ps1 audio subbed.mp4 -bgm bgm.mp3 -o with_bgm.mp4
.\scripts\capcut.ps1 export with_bgm.mp4 -o final.mp4
```

## 與原始 FFmpeg 的關係

```
capcut.ps1 trim    →  ffmpeg -i input -ss start -to end -c:v libx264 -c:a aac output
capcut.ps1 split   →  ffmpeg -i input -ss 0 -to at ... && ffmpeg -i input -ss at ...
capcut.ps1 merge   →  ffmpeg -f concat -i filelist ...
capcut.ps1 text    →  ffmpeg drawtext filter
capcut.ps1 audio   →  ffmpeg amix + volume filter
capcut.ps1 speed   →  ffmpeg setpts + atempo filter
capcut.ps1 subtitle → ffmpeg subtitles filter
capcut.ps1 export  →  ffmpeg -c:v libx264 -c:a aac ...
capcut.ps1 info    →  ffprobe -show_format -show_streams
```

- 所有功能皆有 FFmpeg fallback（本身就是 FFmpeg）
- 若需更精細控制，可直接使用 FFmpeg 命令
- `capcut.ps1` 適用於 80% 的常見操作，複雜濾鏡請用原始 FFmpeg
