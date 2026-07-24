# YouTube Thumbnail Generation

## Overview

為 YouTube 影片產生醒目的自訂縮圖（1280×720），使用大字型影音標題 + 發光效果吸引觀眾點擊。

**工具**：`scripts/thumbnail.py`（基於 Python Pillow）

## Prerequisites

```powershell
pip install Pillow
```

## Usage

### 基本：從圖片產生縮圖

```powershell
python scripts/thumbnail.py --bg background.jpg --title "影片標題" --output thumb.jpg
```

### 從影片擷取畫面做為背景

```powershell
# 從第 10 秒擷取畫面
python scripts/thumbnail.py --video input.mp4 --time 10 --title "超強教學" --subtitle "Complete Tutorial" --output thumb.jpg
```

### 自訂字級與顏色

```powershell
python scripts/thumbnail.py --bg bg.jpg --title "重磅消息" --title-size 120 --subtitle "Breaking News" --text-color "#FFFFFF" --glow "#FF4400" --output thumb.jpg
```

### 無背景圖（自動產生漸層背景）

當 `--bg` 指定的檔案不存在或格式不符時，自動使用深色漸層作為背景：

```powershell
python scripts/thumbnail.py --bg nonexistent.jpg --title "新片上映" --output thumb.jpg
```

## Parameters

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `--bg` | (必填其一) | 背景圖片路徑 (jpg/png/webp) |
| `--video` | (必填其一) | 影片路徑，自動擷取畫面當背景 |
| `--time` | `10` | 從影片第 N 秒擷取畫面 (配合 --video) |
| `--title` | (必填) | 主標題文字（醒目大字） |
| `--subtitle` | 無 | 副標題文字 |
| `--title-size` | `90` | 主標題字級（px） |
| `--sub-size` | `45` | 副標題字級（px） |
| `--text-color` | `#FFFFFF` | 文字顏色（十六進位） |
| `--glow` | `#FF6600` | 發光/外框顏色 |
| `--output` | `thumbnail.jpg` | 輸出 JPEG 路徑 |

## Design Tips

1. **字級要大**：標題建議 80–120px，確保在 YouTube 列表中小圖示也看得見
2. **對比要高**：文字使用白色 + 橘色光暈，在任何背景上都醒目
3. **字數要精簡**：主標題不超過 15 字，副標題不超過 25 字
4. **發光效果**：預設 8px 多層光暈，文字在任何背景上都清晰
5. **漸層覆蓋**：自動從上到下漸暗，確保淺色背景上的文字可讀性
6. **字型支援**：自動使用 Noto Sans TC（繁體中文開源字型），無須手動安裝

## Pipeline Integration

縮圖產生可做為完整管線的最後一步：

```powershell
# 完整產線：影片 → 雙語字幕 → 旁白 → 縮圖
.\full-pipeline.ps1 -InputVideo raw.mp4 -Bilingual -AssFormat -Narrate -NarrateMode intro
python scripts/thumbnail.py --video output/final.mp4 --time 5 `
    --title "超強教學" --subtitle "Complete Guide" --output thumb.jpg
```
