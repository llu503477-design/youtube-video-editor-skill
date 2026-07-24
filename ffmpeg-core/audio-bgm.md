# FFmpeg Core — Audio & Background Music

## Overview

使用 FFmpeg 的 audio filter graph 進行多軌音訊混合、背景音樂疊加、旁白混音、音量調整、淡入淡出等操作。

## Key Filters

| Filter | 用途 | 說明 |
|--------|------|------|
| `amix` | 混合多個音訊流 | 將多軌音訊疊加（如人聲 + BGM） |
| `amerge` | 合併聲道 | 將多個單聲道合併為立體聲 |
| `volume` | 調整音量 | 線性或 dB 增益 |
| `afade` | 淡入淡出 | 音訊漸變效果 |
| `acrossfade` | 跨片段淡出 | 兩個音訊片段之間的平滑過渡 |
| `aloop` | 循環播放 | 將短音訊循環至指定長度 |

## Commands

### 1. Add Background Music（加入背景音樂）

**基本混合（原始音訊 + BGM，以最短長度為準）**
```powershell
ffmpeg -i input.mp4 -i bgm.mp3 `
    -filter_complex "[0:a][1:a]amix=inputs=2:duration=shortest:dropout_transition=2[aout]" `
    -map 0:v:0 -map "[aout]" -c:v copy -c:a aac -b:a 192k output.mp4
```

**控制 BGM 音量（降低 BGM 至 30%）**
```powershell
ffmpeg -i input.mp4 -i bgm.mp3 `
    -filter_complex "[1:a]volume=0.3[bgm];[0:a][bgm]amix=inputs=2:duration=shortest:dropout_transition=2[aout]" `
    -map 0:v:0 -map "[aout]" -c:v copy -c:a aac -b:a 192k output.mp4
```

**BGM 循環至影片長度**
```powershell
ffmpeg -i input.mp4 -i bgm.mp3 `
    -filter_complex "[1:a]aloop=loop=-1:size=2e9[bgm_loop];[bgm_loop]volume=0.3[bgm];[0:a][bgm]amix=inputs=2:duration=shortest:dropout_transition=2[aout]" `
    -map 0:v:0 -map "[aout]" -c:v copy -c:a aac -b:a 192k output.mp4
```

### 2. Replace Audio（替換音訊）

```powershell
# 完全替換為新的音訊
ffmpeg -i input.mp4 -i new_audio.mp3 -map 0:v -map 1:a -c:v copy -c:a aac -shortest output.mp4
```

### 3. Narration Auto-Ducking（旁白自動閃避原始音訊）

當旁白播放時，原始音訊自動降低；旁白結束後恢復。這是最適合解說影片的混音方式。

```powershell
# 旁白 + 原始音訊（sidechaincompess 自動 ducking）
ffmpeg -i input.mp4 -i narration.wav `
    -filter_complex `
    "[1:a]adelay=2000|2000[narration];`
     [0:a][narration]sidechaincompress=level_in=1:threshold=0.015:ratio=10:attack=100:release=500:makeup=0[ducked];`
     [ducked][narration]amix=inputs=2:duration=first:weights=1 1[aout]" `
    -map 0:v -map "[aout]" -c:v copy -c:a aac output.mp4
```

**參數說明：**

| 參數 | 值 | 效果 |
|------|-----|------|
| `threshold=0.015` | 音量閾值 | 旁白音量超過此值才觸發 ducking |
| `ratio=10` | 壓縮比 | 原始音訊降至原音量 1/10 |
| `attack=100` | 100ms | 旁白出現後 100ms 開始降音 |
| `release=500` | 500ms | 旁白結束後 500ms 恢復 |
| `adelay=2000` | 2s 延遲 | 影片開頭留 2 秒緩衝 |
| `weights=1 1` | 音量權重 | 兩軌皆 100% 輸出 |

### 4. Three-Layer Mix: Narration + Original Audio + BGM（三層混音）

完整的解說影片混音：旁白 duck 原始音訊，BGM 做背景襯底。

```powershell
ffmpeg -i input.mp4 -i narration.wav -i bgm.mp3 `
    -filter_complex `
    "[1:a]adelay=2000|2000[narration];`
     [0:a][narration]sidechaincompress=level_in=1:threshold=0.015:ratio=8:attack=100:release=500[ducked];`
     [2:a]volume=0.15[bgm];`
     [ducked][narration]amix=inputs=2:duration=first[mix1];`
     [mix1][bgm]amix=inputs=2:duration=first:weights=1 0.15[aout]" `
    -map 0:v -map "[aout]" -c:v copy -c:a aac output.mp4
```

**音量比例建議：**

| 音軌 | 比例 | 說明 |
|------|------|------|
| 旁白 | 100% (0dB) | 主要音軌 |
| 原始音訊 | 旁白時 ~10-30%，無旁白時 100% | 由 ducking 自動控制 |
| BGM | 12-15% (-16dB 左右) | 襯底不搶焦點 |

### 5. Mix Three Audio Sources Static（三軌固定音量混合）

```powershell
# 原始音訊(30%) + 旁白(100%) + BGM(20%)
ffmpeg -i input.mp4 -i narration.mp3 -i bgm.mp3 `
    -filter_complex "[0:a]volume=0.3[orig];[1:a]volume=1.0[narr];[2:a]volume=0.2[bgm];[orig][narr][bgm]amix=inputs=3:duration=longest[aout]" `
    -map 0:v -map "[aout]" -c:v copy -c:a aac output.mp4
```

### 6. Add Fade In/Out（加入淡入淡出）

```powershell
ffmpeg -i input.mp4 -i bgm.mp3 `
    -filter_complex `
    "[1:a]volume=0.3,afade=t=in:st=0:d=3,afade=t=out:st=27:d=3[bgm];`
     [0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]" `
    -map 0:v -map "[aout]" -c:v copy -c:a aac output.mp4
```

### 7. BGM auto-ducking（BGM 自動閃避人聲）

當人聲出現時自動降低 BGM 音量，人聲結束後恢復。

```powershell
# 使用 sidechaincompress 實現 ducking
ffmpeg -i input.mp4 -i bgm.mp3 `
    -filter_complex `
    "[1:a]volume=0.8[bgm];`
     [0:a][bgm]sidechaincompress=threshold=-20dB:ratio=5:attack=10:release=200:makeup=1[bgm_ducked];`
     [0:a][bgm_ducked]amix=inputs=2:duration=first[aout]" `
    -map 0:v -map "[aout]" -c:v copy -c:a aac output.mp4
```

### 8. Crossfade Between Audio Segments（音訊過渡）

```powershell
# 兩個音訊片段間淡入淡出
ffmpeg -i intro.mp3 -i main.mp3 -i outro.mp3 `
    -filter_complex `
    "[0:a][1:a]acrossfade=d=2:c1=tri:c2=exp[mid];`
     [mid][2:a]acrossfade=d=3:c1=tri:c2=exp[out]" `
    -map "[out]" combined.mp3
```

### 9. Audio Normalization（音量正規化）

```powershell
# 使用 loudnorm（EBU R128 標準）
ffmpeg -i input.mp4 -af loudnorm=I=-16:LRA=11:TP=-1.5 -c:v copy output.mp4

# 簡單峰值正規化
ffmpeg -i input.mp4 -af volume=3dB -c:v copy output.mp4
```

### 10. Adjust Audio Delay（音訊延遲調整）

```powershell
# 音訊延遲 0.5 秒
ffmpeg -i input.mp4 -af adelay=500|500 -c:v copy output.mp4

# 音訊提前 0.3 秒（負延遲 = 提前，需要先提取再合併）
ffmpeg -i input.mp4 -af atrim=start=0.3 -c:v copy output.mp4
```

## Pro Tips

1. **amix vs amerge**：
   - `amix`：將多軌音訊**疊加**（適合 BGM + 人聲）
   - `amerge`：將多軌音訊**串聯聲道**（適合將左+右聲道合成立體聲）

2. **音量建議比例**：
   - 人聲/旁白：0dB（基準）
   - BGM（有人聲時）：-12dB ~ -8dB（約 0.25~0.4）
   - BGM（無人聲時）：-6dB ~ -3dB（約 0.5~0.7）
   - 音效/SFX：-3dB ~ 0dB

3. **輸出音量標準**：
   - YouTube：-14 LUFS（整合）
   - Spotify：-14 LUFS
   - Apple Music：-16 LUFS
   - 一般 podcast：-16 LUFS

4. **sidechaincompress 調參建議**：
   - `threshold`：人聲觸發閾值（-20dB 起或 absolute 0.015）
   - `ratio`：壓縮比（4:1~10:1）
   - `attack`：壓縮啟動時間（旁白 duck：100ms，BGM duck：5~20ms）
   - `release`：恢復時間（旁白 duck：500ms，BGM duck：100~200ms）
   - 旁白 duck 使用較慢的 attack/release 讓音量過渡更自然

5. **旁白混音要點**：
   - 旁白音軌需要與字幕時間對齊，使用 `adelay` 設定延遲
   - 三層混音順序：先旁白 duck 原始音訊，再混合 BGM
   - BGM 音量建議比一般更低（12-15%）以避免蓋過旁白
   - 若旁白有殘音或爆音，使用 `compand` filter 做動態壓縮

## Verification

```powershell
# 檢查音訊串流
ffprobe -v error -show_entries stream=index,codec_name,channels,sample_rate -select_streams a output.mp4

# 分析音量（EBU R128）
ffmpeg -i output.mp4 -af loudnorm=print_format=json -f null -
```
