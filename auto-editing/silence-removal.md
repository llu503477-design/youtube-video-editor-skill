# Auto Editing — Silence Removal

## Overview

自動移除影片中的靜音段落是提升影片節奏感最有效的方式。本文件涵蓋兩種主要方法：
1. **auto-editor**（推薦）：專用的自動影片剪輯工具，功能完整且維護活躍
2. **純 FFmpeg silencedetect**：不需額外安裝，但操作較複雜

## Tool: auto-editor

### Installation

```powershell
# Windows (winget)
winget install auto-editor

# macOS
brew install auto-editor

# Linux / Docker
docker run wyattblue/auto-editor

# Python pip
pip install auto-editor
```

官網：https://auto-editor.com
原始碼：https://github.com/WyattBlue/auto-editor

### Basic Usage

```powershell
# 最基本用法：移除靜音段落
auto-editor input.mp4 --output output.mp4

# 自訂靜音閾值（預設 -20dB）
auto-editor input.mp4 --edit audio:threshold:-30dB --output output.mp4

# 自訂最小靜音長度（預設 2 秒）
auto-editor input.mp4 --edit audio:min-silence:1.5 --output output.mp4
```

### Advanced Options

```powershell
# 混合模式：靜音移除 + 非靜音加速
auto-editor input.mp4 --edit audio:threshold:-20dB --when:inactive speed:1.5 --output output.mp4

# 輸出剪輯片段（而非完整影片）
auto-editor input.mp4 --export clip-sequence --output clip_%03d.mp4

# 匯出到 Adobe Premiere Pro
auto-editor input.mp4 --export premiere --output project.xml

# 匯出到 DaVinci Resolve
auto-editor input.mp4 --export resolve --output project.xml

# 匯出到 Final Cut Pro
auto-editor input.mp4 --export final-cut-pro --output project.xml

# 只輸出被剪掉的部分（反向操作）
auto-editor input.mp4 --when-active cut --when-inactive nil --output removed.mp4
```

### Silence Detection Parameters

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `threshold` | -20dB | 靜音判定音量閾值 |
| `min-silence` | 2.0s | 最短靜音長度（低於此不剪） |
| `min-loud` | 0.1s | 最短非靜音長度（低於此不保留） |
| `silence-speed` | 0 (cut) | 靜音段落播放速度（0=剪掉） |
| `loud-speed` | 1.0 | 非靜音段落播放速度 |

### Workflow: Remove Silence + Add BGM + Subtitles

```powershell
# Step 1: 移除靜音
auto-editor input.mp4 --edit audio:threshold:-20dB --output no_silence.mp4

# Step 2: 加入 BGM
ffmpeg -i no_silence.mp4 -i bgm.mp3 -filter_complex "[1:a]volume=0.3[bgm];[0:a][bgm]amix=inputs=2:duration=shortest:dropout_transition=2[aout]" -map 0:v -map "[aout]" -c:v copy -c:a aac output_temp.mp4

# Step 3: 燒錄字幕
ffmpeg -i output_temp.mp4 -vf "subtitles=captions.srt:force_style='FontName=Noto Sans TC,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=50,BorderStyle=1'" -c:v libx264 -crf 23 -c:a copy final.mp4

# 清理暫存
Remove-Item no_silence.mp4, output_temp.mp4
```

## Alternative: Pure FFmpeg silencedetect

當無法安裝 auto-editor 時，可使用 FFmpeg 內建的 `silencedetect` filter。

### Step 1: 偵測靜音段落

```powershell
ffmpeg -i input.mp4 -af silencedetect=n=-30dB:d=1 -f null - 2> silence_log.txt
```

輸出範例：
```
[silencedetect @ ...] silence_start: 12.345
[silencedetect @ ...] silence_end: 15.678 | silence_duration: 3.333
```

### Step 2: 建立 filter 指令

根據偵測結果建立 select filter：
```powershell
# 影片 filter（保留非靜音段落）
select='between(t,0,12.345)+between(t,15.678,end)', setpts=N/FRAME_RATE/TB

# 音訊 filter
aselect='between(t,0,12.345)+between(t,15.678,end)', asetpts=N/SR/TB
```

### Step 3: 套用剪輯

```powershell
ffmpeg -i input.mp4 -filter_script:v video_filter.txt -filter_script:a audio_filter.txt output.mp4
```

## Tool Comparison

| 特性 | auto-editor | FFmpeg silencedetect | jumpcutter |
|------|------------|---------------------|------------|
| 安裝難度 | 簡單 | 內建（無需安裝） | pip install |
| 速度 | 快（原生 Nim） | 中等 | 慢（Python） |
| 精準度 | 高 | 高 | 中等 |
| 匯出到 NLE | ✅ Premiere/Resolve/FCP | ❌ | ❌ |
| 批次處理 | ✅ | ❌（需腳本） | ✅ |
| 門檻調整 | ✅ 多參數 | ✅ 基礎參數 | ✅ 基礎參數 |
| 維護狀態 | 活躍（4.5k stars） | 內建於 FFmpeg | 較少更新（156 stars） |

## Best Practices

1. **閾值選擇**：
   - 安靜環境錄音：-30dB ~ -20dB
   - 背景雜音較多：-25dB ~ -15dB
   - 音樂/ podcast：-35dB ~ -25dB

2. **最小靜音長度**：
   - 教學影片：0.5s ~ 1.0s（保留思考暫停）
   - 快速節奏內容：0.3s ~ 0.5s
   - Podcast：0.8s ~ 1.5s

3. **事前準備**：
   - 先處理音訊（降噪、正規化）可提升偵測準確度
   - 較長影片先分段處理再合併

## Verification

```powershell
# 比較前後長度
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 input.mp4
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 output.mp4

# 抽查剪輯點是否自然（建議手動檢查 3-5 處）
```
