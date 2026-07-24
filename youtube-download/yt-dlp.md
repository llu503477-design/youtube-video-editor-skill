# YouTube Download — yt-dlp

## Overview

yt-dlp 是功能最完整的命令列影片下載工具，支援 YouTube 及 1000+ 網站。
本文件涵蓋從基本下載到進階處理的完整操作指南。

## Installation

```powershell
# Windows (winget)
winget install yt-dlp

# Windows (scoop)
scoop install yt-dlp

# macOS
brew install yt-dlp

# Python pip
pip install yt-dlp
```

### 確認 FFmpeg 相依性

yt-dlp 需要 FFmpeg 來合併影片+音訊串流和進行後處理：
```powershell
ffmpeg -version
```

建議使用 yt-dlp 團隊維護的 FFmpeg build：
```powershell
# 下載 FFmpeg builds
# https://github.com/yt-dlp/FFmpeg-Builds/releases
```

## Basic Usage

### 下載影片

```powershell
# 基本下載（最佳品質）
yt-dlp "https://www.youtube.com/watch?v=VIDEO_ID"

# 指定輸出檔名
yt-dlp -o "%(title)s.%(ext)s" "URL"

# 下載到指定目錄
yt-dlp -o "D:\videos\%(title)s.%(ext)s" "URL"

# 合併為 MP4
yt-dlp -f "bestvideo+bestaudio" --merge-output-format mp4 "URL"
```

## Format Selection

### 列出可用格式

```powershell
yt-dlp -F "URL"
```

### 手動選擇格式

```powershell
# 最佳畫質 + 最佳音訊
yt-dlp -f "bestvideo+bestaudio" "URL"

# 特定解析度（1080p）
yt-dlp -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" "URL"

# 僅下載音訊（最高品質）
yt-dlp -f "bestaudio" "URL"
```

## Audio Extraction

```powershell
# 下載並轉換為 MP3
yt-dlp -x --audio-format mp3 "URL"

# 下載並轉換為 Opus
yt-dlp -x --audio-format opus "URL"

# 保留原始編碼
yt-dlp -x --audio-format best "URL"

# 指定音訊品質
yt-dlp -x --audio-format mp3 --audio-quality 0 "URL"
```

## Subtitle Downloading

```powershell
# 下載字幕
yt-dlp --write-subs --sub-lang en "URL"

# 下載自動產生字幕
yt-dlp --write-auto-subs --sub-lang en "URL"

# 內嵌字幕
yt-dlp --write-subs --sub-lang en --embed-subs "URL"

# 多語言字幕
yt-dlp --write-subs --sub-lang en,zh-Hans,ja "URL"

# 下載字幕 + 轉換為 SRT
yt-dlp --write-subs --sub-lang en --convert-subs srt "URL"
```

## Playlist & Channel

```powershell
# 下載整個播放清單
yt-dlp "https://www.youtube.com/playlist?list=PLAYLIST_ID"

# 自訂播放清單輸出命名
yt-dlp -o "%(playlist_index)s - %(title)s.%(ext)s" "PLAYLIST_URL"

# 下載範圍（第 1-5 部影片）
yt-dlp --playlist-start 1 --playlist-end 5 "PLAYLIST_URL"

# 下載整頻道
yt-dlp "https://www.youtube.com/@CHANNEL_NAME/videos"

# 只下載最近 N 部影片
yt-dlp --playlist-end 10 "CHANNEL_URL"
```

## Advanced Features

### 章節分割

```powershell
# 根據章節標記分割
yt-dlp --split-chapters -o "%(title)s - %(chapter)s.%(ext)s" "URL"
```

### SponsorBlock 整合

```powershell
# 標記贊助段落
yt-dlp --sponsorblock-mark all "URL"

# 移除贊助段落
yt-dlp --sponsorblock-remove all "URL"

# 只移除贊助 + 自訂章節
yt-dlp --sponsorblock-remove sponsor,intro,outro "URL"
```

### Cookie 認證

```powershell
# 使用瀏覽器 cookies
yt-dlp --cookies-from-browser chrome "URL"

# 使用 cookies 檔案
yt-dlp --cookies cookies.txt "URL"
```

### 下載限制與排程

```powershell
# 限制下載速度
yt-dlp --limit-rate 5M "URL"

# 僅下載新影片（使用存檔）
yt-dlp --download-archive downloaded.txt "PLAYLIST_URL"

# 避免重複下載
yt-dlp --no-overwrites "PLAYLIST_URL"
```

## Common Use Cases

### Case 1: 下載後自動轉錄 + 加入字幕

```powershell
# download-and-subtitle.ps1
param([string]$Url)

# 下載影片
yt-dlp -f "bestvideo+bestaudio" --merge-output-format mp4 -o "video.%(ext)s" $Url

# 提取音訊
ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav

# 轉錄
whisper audio.wav --model small --output_format srt

# 燒錄字幕
ffmpeg -i video.mp4 -vf "subtitles=audio.srt" -c:v libx264 -crf 23 -c:a copy final.mp4

# 清理
Remove-Item audio.wav, video.mp4
Write-Host "Final output: final.mp4"
```

### Case 2: 下載 Podcast 音訊

```powershell
yt-dlp -x --audio-format mp3 --audio-quality 0 `
    --embed-thumbnail --embed-metadata `
    -o "%(title)s.%(ext)s" "URL"
```

### Case 3: 下載 Shorts

```powershell
# 避免下載整個播放清單
yt-dlp --no-playlist "SHORTS_URL"
```

## Configuration

建立 `yt-dlp.conf` 設定檔以套用預設選項：

```
# 預設選項
-f bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best
--merge-output-format mp4
-o D:\videos\%(title)s.%(upload_date>%Y-%m-%d)s.%(ext)s
--no-overwrites
--embed-thumbnail
--embed-metadata
```

使用方式：
```powershell
yt-dlp --config-location yt-dlp.conf "URL"
```

## Verification

```powershell
# 檢查下載的影片
ffprobe -v error -show_entries format=duration,size,bit_rate -of default=noprint_wrappers=1 output.mp4

# 檢查串流
ffprobe -v error -show_entries stream=index,codec_name,codec_type,width,height -of default=noprint_wrappers=1 output.mp4
```

## Common Issues

| 問題 | 原因 | 解決方案 |
|------|------|---------|
| 無法下載 | YouTube 變更協定 | `yt-dlp -U` 更新到最新版 |
| 影音不同步 | 串流合併問題 | 使用 `--merge-output-format mkv` |
| 無法下載高畫質 | 需要 cookies | 使用 `--cookies-from-browser chrome` |
| 年齡限制內容 | 需要登入 | 使用 cookies 登入 |
| 下載速度慢 | 限制或 IP 問題 | 嘗試 `--limit-rate` 或 proxy |
