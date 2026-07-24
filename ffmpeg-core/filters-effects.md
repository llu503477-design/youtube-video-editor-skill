# FFmpeg Core — Filters & Effects

## Overview

使用 FFmpeg 的 video filter graph 為影片套用濾鏡、特效、轉場、浮水印和文字疊加。

## Key Video Filters

| Filter | 用途 | 說明 |
|--------|------|------|
| `hue` | 色相/飽和度調整 | 色彩校正 |
| `eq` | 亮度/對比度調整 | 曝光校正 |
| `colorbalance` | 色彩平衡 | shadows/midtones/highlights |
| `curves` | 曲線調整 | 精確色彩控制 |
| `blur` / `boxblur` | 模糊效果 | 高斯模糊/方框模糊 |
| `sharpness` | 銳化 | 提升細節清晰度 |
| `drawtext` | 文字疊加 | 標題、時間戳、浮水印 |
| `overlay` | 圖層疊加 | 圖片浮水印、子母畫面 |
| `fps` | 影格率轉換 | 降低或提高 FPS |
| `negate` | 負片效果 | 色彩反轉 |
| `edgedetect` | 邊緣偵測 | 卡通/素描效果 |
| `colorchannelmixer` | 色頻混合 | 自訂色彩映射 |

## Commands

### 1. Color Adjustments（色彩調整）

```powershell
# 亮度、對比度、飽和度
ffmpeg -i input.mp4 -vf "eq=brightness=0.05:contrast=1.2:saturation=1.5" -c:v libx264 -crf 23 -c:a copy output.mp4

# 色相旋轉
ffmpeg -i input.mp4 -vf "hue=H=90:s=1.5" -c:v libx264 -crf 23 -c:a copy output.mp4

# 色彩平衡（shadows / midtones / highlights）
ffmpeg -i input.mp4 -vf "colorbalance=rs=0.1:gs=-0.1:bs=0.05:rh=0.05:gh=0.0:bh=0.0" -c:v libx264 -crf 23 -c:a copy output.mp4
```

### 2. Vintage / Retro Looks（復古風格）

```powershell
# Sepia（復古棕褐色）
ffmpeg -i input.mp4 -vf "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,curves=vintage" -c:v libx264 -crf 23 -c:a copy output.mp4

# 黑白影片
ffmpeg -i input.mp4 -vf "hue=s=0" -c:v libx264 -crf 23 -c:a copy output.mp4

# 舊電視效果（低影格率 + 雜訊）
ffmpeg -i input.mp4 -vf "fps=15,hue=s=0.3,noise=alls=20:allf=t" -c:v libx264 -crf 23 -c:a copy output.mp4
```

### 3. Blur Effects（模糊效果）

```powershell
# 高斯模糊
ffmpeg -i input.mp4 -vf "gblur=sigma=5" -c:v libx264 -crf 23 -c:a copy output.mp4

# 方框模糊
ffmpeg -i input.mp4 -vf "boxblur=10:5" -c:v libx264 -crf 23 -c:a copy output.mp4

# 局部模糊（模糊特定區域）
ffmpeg -i input.mp4 -vf "split[a][b];[a]crop=200:200:100:100,boxblur=10[blur];[b][blur]overlay=100:100" -c:v libx264 -crf 23 -c:a copy output.mp4
```

### 4. Text Overlay（文字疊加）

```powershell
# 基本文字疊加
ffmpeg -i input.mp4 -vf "drawtext=text='Hello World':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2" -c:v libx264 -crf 23 -c:a copy output.mp4

# 時間戳疊加
ffmpeg -i input.mp4 -vf "drawtext=text='%{pts\:gmtime\:0\:%H\\\\\:%M\\\\\:%S}':fontsize=24:fontcolor=white:x=10:y=10" -c:v libx264 -crf 23 -c:a copy output.mp4

# 底部跑馬燈字幕
ffmpeg -i input.mp4 -vf "drawtext=text='Breaking News':fontsize=36:fontcolor=yellow:x=w-mod(t*200\,w+text_w):y=h-th-20" -c:v libx264 -crf 23 -c:a copy output.mp4
```

### 5. Watermark（浮水印）

```powershell
# 圖片浮水印（右下角）
ffmpeg -i input.mp4 -i logo.png -filter_complex "[0:v][1:v]overlay=W-w-10:H-h-10" -c:v libx264 -crf 23 -c:a copy output.mp4

# 半透明浮水印
ffmpeg -i input.mp4 -i logo.png -filter_complex "[1:v]format=rgba,colorchannelmixer=aa=0.5[logo];[0:v][logo]overlay=10:10" -c:v libx264 -crf 23 -c:a copy output.mp4
```

### 6. Picture-in-Picture（子母畫面）

```powershell
ffmpeg -i main.mp4 -i pip.mp4 `
    -filter_complex "[1:v]scale=320:240[pip];[0:v][pip]overlay=W-w-10:H-h-10" `
    -c:v libx264 -crf 23 -c:a aac output.mp4
```

### 7. Transitions（轉場效果）

**交叉淡化**
```powershell
ffmpeg -i clip1.mp4 -i clip2.mp4 `
    -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" `
    -map "[outv]" -map "[outa]" -c:v libx264 -crf 23 -c:a aac output.mp4
```

**淡入/淡出**
```powershell
ffmpeg -i input.mp4 -vf "fade=t=in:st=0:d=2,fade=t=out:st=28:d=3" -c:v libx264 -crf 23 -c:a aac output.mp4
```

### 8. GPU-Accelerated Filters（GPU 加速濾鏡）

**NVIDIA NVENC + CUDA Filters**
```powershell
# 需要 FFmpeg 編譯時啟用 --enable-cuda-nvscvt
ffmpeg -hwaccel cuda -i input.mp4 -vf "scale_cuda=1920:1080" -c:v h264_nvenc -preset p7 -cq 23 output.mp4
```

### 9. Thumbnail Generation（產生縮圖）

```powershell
# 從第 10 秒產生一張縮圖
ffmpeg -ss 10 -i input.mp4 -vframes 1 -q:v 2 thumbnail.jpg

# 每隔 30 秒產生縮圖
ffmpeg -i input.mp4 -vf "fps=1/30,scale=320:-1" thumbnail_%03d.jpg
```

### 10. Concatenate Multiple Clips with Transitions（串聯片段含轉場）

```powershell
# 3 個片段串聯（無轉場）
ffmpeg -i clip1.mp4 -i clip2.mp4 -i clip3.mp4 `
    -filter_complex "[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[outv][outa]" `
    -map "[outv]" -map "[outa]" -c:v libx264 -crf 23 -c:a aac output.mp4
```

## Pro Tips

1. **多濾鏡串聯**：使用逗號分隔 `-vf "filter1,filter2,filter3"`
2. **濾鏡順序**：先做尺寸變更（scale），再做色彩調整，最後疊加文字/浮水印
3. **效能考量**：GPU 濾鏡（nvenc/cuda）可大幅加速，但色彩精確度可能略低於 CPU
4. **複雜 filter_complex**：建議先寫入檔案再用 `-filter_complex_script` 載入

## Verification

```powershell
# 檢查濾鏡鏈
ffprobe -v error -show_entries stream=codec_name,width,height,pix_fmt -select_streams v output.mp4

# 比較原始與輸出品質（SSIM/PSNR）
ffmpeg -i input.mp4 -i output.mp4 -lavfi "[0:v][1:v]ssim;[0:v][1:v]psnr" -f null -
```
