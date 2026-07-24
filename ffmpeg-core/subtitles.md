# FFmpeg Core — Subtitles / Captions

## Overview

使用 FFmpeg 將字幕燒錄（burn/hardcode）進影片，或附加為可切換的軟字幕軌道（soft subs）。

**預設字幕策略：繁體中文（zh-TW）為主體 + 英文（en）為輔助**
- 中文字級 **22px** / 英文字級 **16px**（適用於 1080p 基準，動態縮放）
- 字型 **Noto Sans TC**（Google 思源黑體，開源免費可商用，支援繁體中文）
- **BorderStyle=1**（外框 + 陰影，無底色填充，畫面乾淨）
- 中文顯示於上排，英文顯示於下排
- **動態字級縮放**：系統會自動偵測影片高度，以 1080p 為基準等比縮放

## Subtitle Background Options（字幕背景選擇）

本技能支援兩種字幕背景模式，可透過 `-SubBg` 參數切換（詳見 Pipeline 與 Batch 工作流程）：

| 模式 | BorderStyle | 外觀 | 適用場景 |
|------|------------|------|---------|
| **`none`**（無黑底）✅ 預設 | `1` | 文字 + 輪廓 + 陰影，背景全透明 | 乾淨畫面、Vlog、解說影片 |
| **`black`**（黑底） | `4` | 文字後方有黑色矩形背景（僅包覆文字寬度） | 底色複雜、需遮蓋原始字幕 |

### 無黑底模式（`-SubBg none`）✅ 預設

僅顯示文字本體 + 輪廓線 + 陰影，背景完全透明。
適合畫面乾淨、沒有複雜底色的影片。

```powershell
ffmpeg -i input.mp4 `
    -vf "subtitles=captions.srt:force_style='FontName=Noto Sans TC,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=50,BorderStyle=1'" `
    -c:v libx264 -crf 23 -c:a aac output.mp4
```

### 黑底模式（`-SubBg black`）

在文字後方繪製黑色矩形背景，**寬度僅包覆文字本身**，不是全螢幕寬度。
可提升可讀性，特別是在淺色或複雜背景的影片中。

```powershell
ffmpeg -i input.mp4 `
    -vf "subtitles=captions.srt:force_style='FontName=Noto Sans TC,FontSize=22,PrimaryColour=&H00FFFFFF,BackColour=&H80000000,BorderStyle=4,Outline=0,Shadow=0,MarginV=50'" `
    -c:v libx264 -crf 23 -c:a aac output.mp4
```

> **黑底 vs 全寬 drawbox 的區別**：
> - `BorderStyle=4`：背景框**只包覆字幕文字本身**，隨文字長度變化，非全螢幕寬度
> - `drawbox`：繪製**固定全寬**的矩形區塊（如 `w=iw`），適合遮蓋原始影片的全寬硬編碼字幕
> - 兩者可組合使用（先 drawbox 蓋原始字幕，再用 BorderStyle=4 疊加新字幕）

### ASS 格式的對應設定

ASS 的 `BorderStyle` 欄位控制背景行為：

| BorderStyle | 效果 | 對應 SubBg |
|-------------|------|-----------|
| `1` | 標準輪廓 + 陰影，背景透明 | `none` |
| `3` | 不透明背景框（包覆文字） | `black` |
| `4` | 與 `3` 相同（FFmpeg 支援） | `black` |

ASS 範例（無黑底預設）：
```ass
Style: zh-TW,Noto Sans TC,22,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,2,2,20,20,50,1
                                                        ^^^^^^^^^^         ^
                                                        BackColour=0        BorderStyle=1 → outline+shadow
Style: EN,Arial,16,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,2,2,10,10,30,1
```

---

## Key Tools

## Commands

### 1. Burn SRT Subtitles（基本燒錄）

```powershell
ffmpeg -i input.mp4 -vf "subtitles=captions.srt" -c:v libx264 -crf 23 -c:a copy output.mp4
```

### 2. Styled SRT Subtitles（自訂樣式）

```powershell
ffmpeg -i input.mp4 `
    -vf "subtitles=captions.srt:force_style='FontName=Noto Sans TC,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=50,BorderStyle=1'" `
    -c:v libx264 -crf 23 -c:a aac output.mp4
```

**force_style 參數參考表**

| 參數 | 說明 | 範例值 |
|------|------|--------|
| `FontName` | 字型名稱 | Noto Sans TC, Arial |
| `FontSize` | 字體大小（像素） | 22（中文）/ 16（英文），動態縮放 |
| `PrimaryColour` | 文字顏色（BGR 格式） | `&H00FFFFFF`（白色） |
| `SecondaryColour` | 卡拉 OK 效果顏色 | `&H00FF0000`（藍色） |
| `OutlineColour` | 輪廓顏色 | `&H00000000`（黑色） |
| `BackColour` | 背景/陰影顏色（含 Alpha） | `&HFF000000`（全不透明黑，遮蓋原始字幕） |
| `Outline` | 輪廓粗細（像素） | 2 |
| `Shadow` | 陰影距離（像素） | 1 |
| `Alignment` | 對齊位置（數字鍵盤佈局） | 2（底部置中） |
| `MarginV` | 垂直邊距（像素） | 30 |
| `Bold` | 粗體（0 或 1） | 1 |
| `BorderStyle` | 邊框樣式 | **1（預設，外框+陰影，無底色）**，4（黑底框包覆文字） |

### 3. Burn ASS Subtitles（複雜樣式）

```powershell
# ASS 檔案已包含完整樣式定義
ffmpeg -i input.mp4 -vf "ass=captions.ass" -c:v libx264 -crf 23 -c:a copy output.mp4
```

### 4. Add Soft Subtitles（附加可切換字幕）

```powershell
# 附加為可切換軌道（MP4 使用 mov_text）
ffmpeg -i input.mp4 -i captions.srt -c:v copy -c:a copy -c:s mov_text output.mp4

# 多語言字幕
ffmpeg -i input.mp4 -i captions_en.srt -i captions_zh.srt `
    -map 0:v -map 0:a -map 1 -map 2 `
    -c:v copy -c:a copy -c:s mov_text `
    -metadata:s:s:0 language=eng -metadata:s:s:0 title=English `
    -metadata:s:s:1 language=chi -metadata:s:s:1 title=中文 `
    output.mp4
```

### 5. Extract Subtitles from Video（擷取字幕）

```powershell
# 擷取第一個字幕流為 SRT
ffmpeg -i input.mp4 -map 0:s:0 -c:s srt subs.srt

# 列出所有串流資訊（含字幕）
ffprobe -v error -show_entries stream=index,codec_name,codec_type:stream_tags=language -of default=noprint_wrappers=1 input.mp4
```

### 6. Popular Subtitle Styles（熱門樣式範本）

**YouTube 風格**
```powershell
-force_style 'FontName=Roboto,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=1,Shadow=0'
```

**Netflix 風格**
```powershell
-force_style 'FontName=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00333333,Outline=2,Shadow=0'
```

**Crunchyroll 風格（粗體黃字）**
```powershell
-force_style 'FontName=Arial,FontSize=22,PrimaryColour=&H0000FFFF,Bold=1,OutlineColour=&H00000000,Outline=2,Shadow=1'
```

**無黑底（預設 — SubBg=none，外框+陰影，無底色）**
```powershell
-force_style 'FontName=Noto Sans TC,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,BorderStyle=1'
```

**黑底背景（SubBg=black，文字後方黑底框）**
```powershell
-force_style 'FontName=Noto Sans TC,FontSize=22,PrimaryColour=&H00FFFFFF,BackColour=&H80000000,BorderStyle=4,Outline=0,Shadow=0,MarginV=50'
```

### 7. Bilingual Subtitles（雙語字幕 — 預設 zh-TW + EN）

本技能預設使用繁體中文為主體、英文為輔助的雙語字幕配置。
實現方式有兩種：**合併 SRT 法**（簡單）與 **ASS 雙樣式法**（專業）。

#### 方法 A：合併 SRT 法（簡單快速）

將中文與英文 SRT 合併為單一檔案，中文行在上、英文行在下：

```powershell
# Step 1: Whisper 產生中文 SRT（轉錄）
whisper audio.wav --model small --language zh --task transcribe --output_format srt --output_dir output/zh

# Step 2: 目前 Agent 讀取中文 SRT，只翻譯 cue 文字到 output/en/audio.srt
python scripts/validate_agent_translation.py output/zh/audio.srt output/en/audio.srt

# Step 3: 使用 Python 腳本合併雙語 SRT
python scripts/merge_bilingual_srt.py output/zh/audio.srt output/en/audio.srt bilingual.srt

# Step 4: 燒錄雙語字幕（統一風格）
ffmpeg -i input.mp4 -vf "subtitles=bilingual.srt:force_style='FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2'"
       -c:v libx264 -crf 23 -c:a aac output.mp4
```

**合併腳本** `scripts/merge_bilingual_srt.py`：
```python
# merge_bilingual_srt.py — Merge zh-TW + EN SRT into bilingual SRT
import sys

def parse_srt(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    blocks = content.strip().split('\n\n')
    entries = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            idx = lines[0]
            time_range = lines[1]
            text = '\n'.join(lines[2:])
            entries.append((idx, time_range, text))
    return entries

def merge_bilingual(zh_entries, en_entries):
    merged = []
    for (z_idx, z_time, z_text), (e_idx, e_time, e_text) in zip(zh_entries, en_entries):
        # 使用中文時間軸，中文在上、英文在下
        merged.append(f"{z_idx}\n{z_time}\n{z_text}\n{e_text}\n")
    return merged

if __name__ == '__main__':
    zh_path, en_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    zh = parse_srt(zh_path)
    en = parse_srt(en_path)
    result = merge_bilingual(zh, en)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(result))
    print(f"Bilingual SRT saved to {out_path} ({len(result)} entries)")
```

#### 方法 B：ASS 雙樣式法（專業 — 中文大、英文小）

建立 ASS 字幕檔案，為中文和英文分別定義不同字級樣式：

```powershell
# Python 腳本產生 ASS 雙語字幕（預設 FontSize=22/16，可指定影片高度縮放）
python scripts/generate_bilingual_ass.py output.zh.srt output.en.srt bilingual.ass --background none --video-height 720

# 燒錄 ASS 雙語字幕（使用 Noto Sans TC 開源字型）
ffmpeg -i input.mp4 -vf "ass=bilingual.ass" -c:v libx264 -crf 23 -c:a aac output.mp4
```

**ASS 字幕產生腳本** `scripts/generate_bilingual_ass.py`（實際使用最新版本，含 `--scale`、`--video-height`、`--background` 參數）：

**ASS 樣式說明（v1.2，動態縮放）：**

| 樣式名稱 | 用途 | 字型 | 字級（1080p） | 粗體 | 邊框樣式 | 背景色 | 對齊 |
|---------|------|------|-------------|------|---------|--------|------|
| `zh-TW` | 繁體中文主體 | Noto Sans TC | **22px**（動態：720p→15px, 4K→44px） | **Bold** | **1（外框+陰影，無底色）** | `&H00000000` | 底部置中 |
| `EN` | 英文輔助 | Arial | **16px**（動態：720p→11px, 4K→32px） | 否 | **1（外框+陰影，無底色）** | `&H00000000` | 底部置中 |

#### 方法 D：English→zh-TW 全自動雙語管線（專業）

當原始影片為**英文語音**時，使用此管線自動產生繁體中文 + 英文雙語字幕。
採用 HuggingFace MarianMT 本地翻譯 + OpenCC 繁簡轉換，完全離線執行。

> ⚠️ **v1.2 起 deprecated**：generate_bilingual_from_en.py 不再維護。
> 請改用兩階段：Whisper(zh transcribe) + Whisper(zh→en translate) 搭配 generate_bilingual_ass.py。

**手動分步執行（若需自訂參數）：**

```powershell
# Step 1: 提取音訊
ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav -y

# Step 2: faster-whisper 英文轉錄
python -c "
from faster_whisper import WhisperModel
model = WhisperModel('base', device='cpu', compute_type='int8')
segments, info = model.transcribe('audio.wav', language='en', beam_size=5)
import datetime
with open('subs_en.srt', 'w', encoding='utf-8') as f:
    for i, seg in enumerate(segments, 1):
        start = str(datetime.timedelta(seconds=seg.start))[:-3].replace('.', ',')
        end = str(datetime.timedelta(seconds=seg.end))[:-3].replace('.', ',')
        if start.count(':') == 1: start = '00:' + start
        if end.count(':') == 1: end = '00:' + end
        f.write(f'{i}\n{start} --> {end}\n{seg.text.strip()}\n\n')
"

# Step 3: MarianMT EN→zh-CN 翻譯
python -c "
from transformers import MarianMTModel, MarianTokenizer
model_name = 'Helsinki-NLP/opus-mt-en-zh'
tokenizer = MarianTokenizer.from_pretrained(model_name)
model = MarianMTModel.from_pretrained(model_name)

def parse_srt(path):
    with open(path, encoding='utf-8') as f:
        blocks = f.read().strip().split('\n\n')
    return [('\n'.join(b.split('\n')[2:])) for b in blocks if len(b.split('\n')) >= 3]

texts = parse_srt('subs_en.srt')
inputs = tokenizer(texts, return_tensors='pt', padding=True, truncation=True, max_length=128)
translated = model.generate(**inputs)
zh_texts = [tokenizer.decode(t, skip_special_tokens=True) for t in translated]

with open('subs_zh_cn.srt', 'w', encoding='utf-8') as f:
    for i, (_, block) in enumerate(zip(texts, open('subs_en.srt', encoding='utf-8').read().strip().split('\n\n'))):
        lines = block.split('\n')
        f.write(f'{lines[0]}\n{lines[1]}\n{zh_texts[i]}\n\n')
print('zh-CN translation complete')
"

# Step 4: OpenCC zh-CN→zh-TW 轉換
python -c "
from opencc import OpenCC
cc = OpenCC('s2t')
with open('subs_zh_cn.srt', encoding='utf-8') as f:
    content = f.read()
with open('subs_zh_tw.srt', 'w', encoding='utf-8') as f:
    f.write(cc.convert(content))
print('zh-TW conversion complete')
"

# Step 5: 產生雙語 ASS
python scripts/generate_bilingual_ass.py subs_zh_tw.srt subs_en.srt bilingual.ass

# Step 6: 燒錄字幕
ffmpeg -i input.mp4 -vf "ass=bilingual.ass" -c:v libx264 -crf 18 -c:a aac -b:a 192k output_zhTW_EN.mp4 -y
```

---

#### 方法 C：Youtube API 雙字幕（軟字幕）

當目標平台是 YouTube 時，建議上傳分離的雙語字幕軌道：

```powershell
# 附加為可切換的軟字幕（MP4 格式）
ffmpeg -i input.mp4 -i output.zh.srt -i output.en.srt `
    -map 0:v -map 0:a -map 1 -map 2 `
    -c:v copy -c:a copy -c:s mov_text `
    -metadata:s:s:0 language=chi -metadata:s:s:0 title="中文（繁體）" `
    -metadata:s:s:1 language=eng -metadata:s:s:1 title=English `
    output.mp4
```

---

### 8. Covering Hardcoded Subtitles（遮蓋原始硬編碼字幕）

當原始影片已內嵌燒錄字幕時，使用 `drawbox` + `ass` filter 組合：

```powershell
# 方法一：ASS BorderStyle=4（每行字幕獨立黑底，簡單）
ffmpeg -i input.mp4 -vf "ass=bilingual.ass" -c:v libx264 -crf 18 -c:a aac output.mp4

# 方法二：drawbox 全寬黑底 + ASS（覆蓋整個底部區域，更徹底）
# drawbox 參數：x=0, y=底部往上200px, w=全寬, h=200px, color=全黑
ffmpeg -i input.mp4 -vf "drawbox=x=0:y=ih-200:w=iw:h=200:color=black@1:t=fill,ass=bilingual.ass" -c:v libx264 -crf 18 -c:a aac output.mp4

# 方法三：先使用 generate_bilingual_ass.py 產生雙語 ASS，再燒錄
python scripts/generate_bilingual_ass.py zh.srt en.srt bilingual.ass --background black --video-height 1080
ffmpeg -i input.mp4 -vf "drawbox=x=0:y=ih-200:w=iw:h=200:color=black@1:t=fill,ass=bilingual.ass" -c:v libx264 -crf 18 -c:a aac output.mp4
```

**drawbox 參數說明：**

| 參數 | 值 | 說明 |
|------|-----|------|
| `x=0` | 左側起點 | 從畫面最左邊開始 |
| `y=ih-200` | 底部往上 200px | 1080p 影片中距底部約 18.5% |
| `w=iw` | 全寬 | 覆蓋整個水平寬度 |
| `h=200` | 200px 高 | 足夠覆蓋原始字幕區域 |
| `color=black@1` | 全不透明黑 | Alpha=1（完全不透明） |
| `t=fill` | 填滿模式 | 填滿整個矩形區域 |

### 9. SRT ↔ VTT 轉換

```powershell
# SRT 轉 VTT
ffmpeg -i subs.srt subs.vtt

# VTT 轉 SRT
ffmpeg -i subs.vtt subs.srt
```

## Best Practices

1. **字型支援**：使用開源字型 **Noto Sans TC**（Google/Adobe，SIL OFL，免費可商用）。從 [Google Fonts](https://fonts.google.com/noto) 下載安裝
2. **編碼問題**：SRT 檔案務必使用 UTF-8 編碼，避免中文亂碼
3. **時間軸對齊**：Whisper 生成的 SRT 建議抽查 3 個時間點確認準確性
4. **雙語字幕順序**：預設為**中文在上（主體）、英文在下（輔助）**，符合視覺閱讀動線
5. **動態字級縮放**：以 1080p 為基準（zh=22px / en=16px），系統自動依影片高度調整。使用 `--video-height` 或 `--scale` 參數
6. **縮放範圍參考**：720p→zh≈15px/en≈11px；1080p→zh=22px/en=16px；4K→zh≈44px/en≈32px
7. **同時顯示行數**：雙語最多 2 行（中+英），每行不超過 30 個字元
8. **安全邊距**：`MarginV` 自動縮放（1080p 基準 zh=50px, en=30px）
9. **遮蓋原始字幕**：使用 `SubBg=black`（`BorderStyle=4` + `BackColour=&H80000000`），為每行字幕提供半透明黑底（僅包覆文字寬度）。若需全寬遮罩再搭配 `drawbox`
10. **背景選擇策略**：預設 `SubBg=none`（BordersStyle=1 外框+陰影，畫面乾淨）。淺色/複雜背景或需遮蓋原始字幕時用 `SubBg=black`
11. **雙語工作流**：Whisper 只做中文轉錄；目前 Agent 直接翻譯 cue 文字、保留時間碼並通過 `validate_agent_translation.py`，再用 `generate_bilingual_ass.py` 合併

## Common Issues

| 問題 | 原因 | 解決方案 |
|------|------|---------|
| 字幕沒出現 | 濾鏡未正確載入 | 檢查 SRT 路徑（使用絕對路徑） |
| 中文變亂碼 | 編碼問題 | 確保 SRT 為 UTF-8 編碼 |
| 字型不對 | 系統無該字型 | 使用系統已安裝的字型，或指定字型路徑 |
| 時間軸偏移 | 影格率不一致 | 確認 SRT 的 framerate 與影片匹配 |
| 燒錄失敗無錯誤 | FFmpeg 靜默失敗 | 先轉換 SRT → ASS 再燒錄 |
