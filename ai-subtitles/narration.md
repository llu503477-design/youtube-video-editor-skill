# AI Narration — 影片自動旁白生成

## Overview

本功能為影片加入自動旁白（Voiceover / Narration），將現有字幕轉換為口語解說，
讓原始影片**轉變為全新的解說式影片**。

### 核心流程

```
原始影片 + 字幕
    │
    ├─ 階段分析：依字幕段落切割 (每段 ~15-30s)
    ├─ 旁白稿生成：每段字幕 → 口語解說句
    ├─ TTS 語音合成：選擇語言 + 發音人
    ├─ 旁白音訊輸出：含時間戳記
    └─ 混音：原始音訊自動降音 (ducking) + 旁白疊加
```

### 支援語言

| 語言 | Edge-TTS 發音人 | 語音代碼 |
|------|----------------|---------|
| 繁體中文 (zh-TW) | HsiaoChenNeural / HsiaoYuNeural | `zh-TW-HsiaoChenNeural` |
| 简体中文 (zh-CN) | XiaoxiaoNeural / YunxiNeural | `zh-CN-XiaoxiaoNeural` |
| English (en) | AriaNeural / JennyNeural | `en-US-AriaNeural` |
| 日本語 (ja) | NanamiNeural | `ja-JP-NanamiNeural` |
| 한국어 (ko) | SunHiNeural | `ko-KR-SunHiNeural` |

---

## 安裝相依套件

```powershell
# Edge-TTS（主要 TTS 引擎，免費高品質）
pip install edge-tts

# 驗證安裝
edge-tts --list-voices | Select-String "zh-TW"
```

---

## 使用方法

### 方法一：從字幕自動產生旁白（推薦）

```powershell
# 自動：讀取 SRT 字幕 → 分階段生成旁白 → 輸出 WAV
python scripts/narrate.py --subs subtitles.srt --lang zh-TW --output narration.wav

# 指定發音人
python scripts/narrate.py --subs subtitles.srt --lang zh-TW --voice zh-TW-HsiaoChenNeural --output narration.wav

# 英文旁白
python scripts/narrate.py --subs subtitles.srt --lang en --voice en-US-AriaNeural --output narration.wav
```

### 方法二：自訂旁白稿

提供純文字旁白稿，每行對應一個字幕段落：

```powershell
python scripts/narrate.py --script narration.txt --lang zh-TW --output narration.wav
```

`narration.txt` 格式範例：
```
歡迎收看本集解說，我們將探討這個主題。
首先看到的是第一部分的重點內容。
接下來讓我們深入分析核心技術。
最後來總結一下關鍵發現。
```

### 方法三：完整影片一鍵處理（含字幕）

```powershell
# 從影片自動轉錄 → 旁白 → 混音
python scripts/narrate.py --video input.mp4 --lang zh-TW --output-dir ./output
```

---

### 同步輸出旁白字幕（`--output-subs`）

旁白語音與原始影片字幕的時間軸不同步（因為是重新生成的引導句），
使用 `--output-subs` 可輸出**對齊旁白語音時間軸的字幕檔案**：

```powershell
python scripts/narrate.py --subs subtitles.srt --lang zh-TW --output narration.wav `
    --output-subs narration.srt
```

**效果**：
- 旁白說「歡迎收看，首先我們來看看...」時，字幕同時出現這段文字
- 每段字幕的時間長度 = TTS 語音的實際長度，精準對齊
- 可直接燒錄到影片上：

```powershell
ffmpeg -i video.mp4 -vf "subtitles=narration.srt:force_style='FontName=Noto Sans TC,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=50,BorderStyle=1'"
    -c:v libx264 -crf 23 -c:a copy output.mp4
```

**搭配 `--mode intro`**：觀眾看到引導句的同時聽到旁白，體驗最佳。

---

## 旁白模式

### `--mode intro`（預設 — 階段性介紹）

每段字幕前方加入一句口語引導，將影片切割為多個「章節」：

```
[原始字幕段落 1]  ...  →  "接下來我們看到的是..."
[原始字幕段落 2]  ...  →  "現在讓我們深入了解..."
[原始字幕段落 3]  ...  →  "最後來做個總結..."
```

適合：教學影片、解說影片、新聞摘要

### `--mode full`（全文朗讀）

將字幕文字直接轉為旁白朗讀，無額外引導句。

適合：有聲書、Podcast 風格的影片

### `--mode summary`（摘要旁白）

每段字幕自動摘要為 1-2 句口語說明，適合快速導覽。

---

## 旁白語言選擇（`--lang`）

旁白語言可以獨立於字幕語言設定。常用組合：

| 字幕語言 | 旁白語言 | 適用情境 |
|---------|---------|---------|
| zh-TW | zh-TW | 中文解說中文內容 ✅ 最常見 |
| zh-TW + EN (雙語) | zh-TW | 中文字幕 + 中文旁白 |
| zh-TW + EN (雙語) | en | 中文字幕 + 英文旁白（國際化） |
| en | zh-TW | 英文影片 + 中文旁白（本地化） |
| en | en | 英文解說英文內容 |

---

## 與音訊混音（FFmpeg ducking）

旁白產生後，使用 FFmpeg 進行智慧混音（自動降低原始音量）：

### 基本混音：旁白 + 原始音訊

```powershell
ffmpeg -i video.mp4 -i narration.wav `
    -filter_complex "[1:a]adelay=2000|2000[narration];[0:a][narration]amix=inputs=2:duration=first:weights=0.3 1[aout]" `
    -map 0:v -map "[aout]" -c:v copy -c:a aac output.mp4
```

### 進階 ducking：旁白播放時原始音訊自動降低

使用 `volume` + `sidechaincompress` 或分段音量控制：

```powershell
# 方法 A：sidechain compression（旁白觸發原始音訊降音）
ffmpeg -i video.mp4 -i narration.wav `
    -filter_complex `
    "[1:a]adelay=2000|2000[narration];`n
     [0:a][narration]sidechaincompress=level_in=1:threshold=0.015:ratio=10:attack=100:release=500:makeup=0[ducked];`n
     [ducked][narration]amix=inputs=2:duration=first:weights=1 1[aout]" `
    -map 0:v -map "[aout]" -c:v copy -c:a aac output.mp4
```

**參數說明：**

| 參數 | 值 | 效果 |
|------|-----|------|
| `threshold=0.015` | 音量閾值 | 旁白音量超過此值才觸發 ducking |
| `ratio=10` | 壓縮比 | 原始音訊降至原音量 1/10 |
| `attack=100` | 啟動時間 100ms | 旁白出現後 100ms 開始降音 |
| `release=500` | 釋放時間 500ms | 旁白結束後 500ms 恢復音量 |
| `adelay=2000` | 旁白延遲 2s | 影片開頭留 2 秒緩衝 |

### 三層混音：旁白 + BGM + 原始音訊

```powershell
ffmpeg -i video.mp4 -i narration.wav -i bgm.mp3 `
    -filter_complex `
    "[1:a]adelay=2000|2000[narration];`n
     [0:a][narration]sidechaincompress=level_in=1:threshold=0.015:ratio=10:attack=100:release=500[ducked];`n
     [2:a]volume=0.15[bgm];`n
     [ducked][narration]amix=inputs=2:duration=first:weights=1 1[mix1];`n
     [mix1][bgm]amix=inputs=2:duration=first:weights=1 0.15[aout]" `
    -map 0:v -map "[aout]" -c:v copy -c:a aac output.mp4
```

---

## 完整管線：影片 + 字幕 → 旁白解說影片

```powershell
# Step 1: 產生雙語字幕（如有需要）
pwsh -File scripts/whisper-cli.ps1 audio.wav -Language zh -Task transcribe -OutputPrefix output/zh/audio
pwsh -File scripts/whisper-cli.ps1 audio.wav -Language zh -Task translate -OutputPrefix output/en/audio
python scripts/merge_bilingual_srt.py audio.zh.srt audio.en.srt bilingual.srt

# Step 2: 從字幕產生旁白（繁體中文，分階段介紹）
python scripts/narrate.py --subs bilingual.srt --lang zh-TW --mode intro --output narration.wav

# Step 3: 混音（旁白 + 原始音訊 + BGM，含 ducking）
ffmpeg -i input.mp4 -i narration.wav -i bgm.mp3 `
    -filter_complex `
    "[1:a]adelay=2000|2000[narration];`n
     [0:a][narration]sidechaincompress=level_in=1:threshold=0.015:ratio=8:attack=100:release=500[ducked];`n
     [2:a]volume=0.12[bgm];`n
     [ducked][narration]amix=inputs=2:duration=first[mix1];`n
     [mix1][bgm]amix=inputs=2:duration=first:weights=1 0.15[aout]" `
    -map 0:v -map "[aout]" -c:v libx264 -crf 23 -c:a aac output.mp4

# Step 4: 燒錄字幕
ffmpeg -i output.mp4 -vf "ass=bilingual.ass" -c:v libx264 -crf 23 -c:a copy final.mp4
```

---

## 語言切換範例

### 中文影片 + 英文旁白（國際化）

```powershell
python scripts/narrate.py --subs bilingual.srt --lang en --voice en-US-AriaNeural --mode intro --output narration_en.wav
```

### 英文影片 + 中文旁白（本地化）

```powershell
# Step 1: 英文轉錄
pwsh -File scripts/whisper-cli.ps1 audio.wav -Language en -OutputPrefix output/en/audio

# Step 2: 中文旁白（即使原始字幕是英文）
python scripts/narrate.py --subs audio.srt --lang zh-TW --voice zh-TW-HsiaoChenNeural --output narration_zh.wav
```

---

## Edge-TTS 語音清單（常用）

```powershell
# 列出所有語言的所有發音人
edge-tts --list-voices

# 列出特定語言的發音人
edge-tts --list-voices | Select-String "zh-TW"
edge-tts --list-voices | Select-String "zh-CN"
edge-tts --list-voices | Select-String "en-US"
```

### 推薦發音人

| 語言 | 推薦發音人 | 性別 | 風格 |
|------|-----------|------|------|
| 繁體中文 | `zh-TW-HsiaoChenNeural` | 女聲 | 自然解說 |
| 繁體中文 | `zh-TW-HsiaoYuNeural` | 女聲 | 親切活潑 |
| 繁體中文 | `zh-TW-YunJheNeural` | 男聲 | 沉穩解說 |
| 简体中文 | `zh-CN-XiaoxiaoNeural` | 女聲 | 自然流暢 |
| 简体中文 | `zh-CN-YunxiNeural` | 男聲 | 解說風格 |
| 美式英語 | `en-US-AriaNeural` | 女聲 | 專業解說 |
| 美式英語 | `en-US-GuyNeural` | 男聲 | 活力解說 |
| 英式英語 | `en-GB-SoniaNeural` | 女聲 | 優雅英國腔 |
| 日語 | `ja-JP-NanamiNeural` | 女聲 | 標準日語 |
| 韓語 | `ko-KR-SunHiNeural` | 女聲 | 標準韓語 |

---

## 旁白稿自動生成策略

`narrate.py` 使用模板化策略產生分階段旁白，無需 LLM API：

### intro 模式（預設）

每段前方加入階段性引導句，依段落位置自動變化：

| 段落位置 | 繁體中文引導句 | English Guide |
|---------|---------------|---------------|
| 第 1 段 | 「歡迎收看，首先我們來看…」 | "Welcome! First, let's look at..." |
| 第 2 段 | 「接下來讓我們了解…」 | "Next, let's understand..." |
| 第 3 段 | 「現在進一步探討…」 | "Now let's dive deeper into..." |
| 第 4 段 | 「另一方面，我們看到…」 | "On the other hand, we see..." |
| 倒數第 2 段 | 「最後關鍵的一點是…」 | "A key point to note is..." |
| 最後 1 段 | 「總結來說…」 | "In conclusion..." |

### full 模式

直接朗讀字幕原文，不添加引導句。

### summary 模式

取字幕原文的前 80 個字元作為摘要旁白，適合快速帶過。

---

## 品質檢查

- [ ] 旁白語言與影片內容匹配
- [ ] 旁白時間點與字幕段落對齊
- [ ] 原始音訊 ducking 效果自然（無突兀音量跳動）
- [ ] BGM 音量不蓋過旁白
- [ ] 分階段引導句流暢不重複
- [ ] 旁白結尾無殘音或截斷

---

## Troubleshooting

| 問題 | 原因 | 解決方案 |
|------|------|---------|
| `edge-tts` not found | 未安裝 | `pip install edge-tts` |
| 旁白與畫面不同步 | adelay 設定不當 | 調整 `adelay` 毫秒數，或使用 narrate.py 的 `--offset` |
| ducking 效果太突兀 | attack/release 過短 | 增加 `attack=200` `release=1000` |
| 旁白語言錯誤 | voice 不支援指定語言 | 確認 voice 與 lang 匹配（如 zh-TW 配 zh-TW 的 voice） |
| 中文發音不標準 | 選到簡體中文發音人 | 使用 `zh-TW-*` 發音人 |
| 段落間無 pause | 旁白連續無間隔 | 使用 `--pause 500` 設定段落間隔毫秒 |
