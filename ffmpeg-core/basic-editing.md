# FFmpeg Core — Basic Video Editing

## Overview

FFmpeg 是影片編輯的核心引擎。本文件涵蓋所有基礎編輯操作：裁剪、合併、裁切、縮放、速度調整、格式轉換。

## Commands

### 1. Trim / Cut Video（裁剪影片）

**精確裁剪（重新編碼，影格精準）**
```powershell
ffmpeg -i input.mp4 -ss 00:01:30 -t 00:00:45 -c:v libx264 -crf 23 -c:a aac output.mp4
```
- `-ss 00:01:30`：開始時間（1分30秒）
- `-t 00:00:45`：持續時間（45秒）
- `-to 00:02:15`：結束時間（替代 -t）

**快速裁剪（串流複製，無損但非影格精準）**
```powershell
ffmpeg -ss 00:01:30 -i input.mp4 -t 00:00:45 -c:v copy -c:a copy output.mp4
```
> 注意：`-ss` 放在 `-i` 前可加速搜尋，但關鍵影格可能不精準。

### 2. Merge / Concatenate Videos（合併影片）

**相同編碼參數的檔案（最快方式）**
```powershell
# 先建立檔案清單 filelist.txt：
# file 'clip1.mp4'
# file 'clip2.mp4'
# file 'clip3.mp4'

ffmpeg -f concat -safe 0 -i filelist.txt -c:v copy -c:a copy output.mp4
```

**不同編碼參數的檔案（重新編碼）**
```powershell
ffmpeg -i clip1.mp4 -i clip2.mp4 -i clip3.mp4 `
    -filter_complex "[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[outv][outa]" `
    -map "[outv]" -map "[outa]" -c:v libx264 -crf 23 -c:a aac output.mp4
```

### 3. Crop Video（裁切）

```powershell
ffmpeg -i input.mp4 -vf "crop=1280:720:0:0" -c:v libx264 -crf 23 -c:a copy output.mp4
```
- `crop=寬:高:x:y` — 從 (x, y) 開始裁切指定寬高的區域

**自動裁切黑色邊框**
```powershell
ffmpeg -i input.mp4 -vf "cropdetect" -f null - 2>&1 | findstr "crop="
# 然後使用偵測到的值
ffmpeg -i input.mp4 -vf "crop=720:720:100:0" -c:v libx264 -crf 23 -c:a copy output.mp4
```

### 4. Resize / Scale（縮放）

```powershell
# 指定寬度，自動計算高度
ffmpeg -i input.mp4 -vf "scale=1280:-1" -c:v libx264 -crf 23 -c:a copy output.mp4

# 指定高度，自動計算寬度
ffmpeg -i input.mp4 -vf "scale=-1:720" -c:v libx264 -crf 23 -c:a copy output.mp4

# 強制指定尺寸（可能變形）
ffmpeg -i input.mp4 -vf "scale=1920:1080:force_original_aspect_ratio=decrease" -c:v libx264 -crf 23 -c:a aac output.mp4
```

### 5. Speed Change（速度調整）

```powershell
# 加速 2 倍
ffmpeg -i input.mp4 -vf "setpts=0.5*PTS" -af "atempo=2.0" output.mp4

# 慢動作 0.5 倍
ffmpeg -i input.mp4 -vf "setpts=2.0*PTS" -af "atempo=0.5" output.mp4

# 注意：atempo 範圍限制 0.5~2.0，如需更極端的速度需串聯
# 加速 4 倍 = atempo=2.0,atempo=2.0
ffmpeg -i input.mp4 -vf "setpts=0.25*PTS" -af "atempo=2.0,atempo=2.0" output.mp4
```

### 6. Format Conversion（格式轉換）

```powershell
# MP4 → WebM (VP9)
ffmpeg -i input.mp4 -c:v libvpx-vp9 -crf 30 -b:v 0 -c:a libopus output.webm

# MP4 → AVI
ffmpeg -i input.mp4 -c:v mpeg4 -q:v 5 -c:a mp3 output.avi

# MOV → MP4
ffmpeg -i input.mov -c:v libx264 -crf 23 -c:a aac output.mp4

# MP4 → GIF
ffmpeg -i input.mp4 -vf "fps=10,scale=480:-1:flags=lanczos" -c:v gif output.gif
```

### 7. Extract Audio（擷取音訊）

```powershell
# 擷取為 MP3
ffmpeg -i input.mp4 -vn -acodec mp3 -ar 44100 -ac 2 output.mp3

# 擷取為 WAV（適合 Whisper 處理）
ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav

# 擷取為 AAC（保持原始編碼）
ffmpeg -i input.mp4 -vn -c:a copy audio.aac
```

### 8. Rotate / Flip（旋轉 / 翻轉）

```powershell
# 順時針旋轉 90 度
ffmpeg -i input.mp4 -vf "transpose=1" output.mp4

# 逆時針旋轉 90 度
ffmpeg -i input.mp4 -vf "transpose=2" output.mp4

# 水平翻轉
ffmpeg -i input.mp4 -vf "hflip" output.mp4

# 垂直翻轉
ffmpeg -i input.mp4 -vf "vflip" output.mp4
```

## Pro Tips

1. **CRF 值指南**：18=無損視覺品質，23=預設（良好平衡），28=較小檔案，35=高壓縮
2. **preset 選項**：`ultrafast` > `superfast` > `veryfast` > `faster` > `fast` > `medium` > `slow` > `slower` > `veryslow`（越慢壓縮率越好）
3. **硬體加速編碼**：
   - NVIDIA: `-c:v h264_nvenc` 或 `-c:v hevc_nvenc`
   - AMD: `-c:v h264_amf` 或 `-c:v hevc_amf`
   - Intel: `-c:v h264_qsv` 或 `-c:v hevc_qsv`
4. 先使用 `-c:v copy` 快速測試命令是否正確，再改用重新編碼

## Verification

```powershell
# 檢查輸出檔案
ffprobe -v error -show_entries format=duration,size,bit_rate -of default=noprint_wrappers=1 output.mp4

# 檢查影格完整性
ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_frames -of default=noprint_wrappers=1 output.mp4
```
