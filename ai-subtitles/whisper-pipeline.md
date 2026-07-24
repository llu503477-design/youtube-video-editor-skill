# AI Subtitles — Whisper Pipeline

## Overview

使用 OpenAI Whisper 及其衍生專案（whisper.cpp / faster-whisper）將語音自動轉換為文字字幕。
支援 99+ 種語言，輸出 SRT、VTT、TXT 等格式。

**預設語言：繁體中文（zh-TW / zh）**。所有範例以中文轉錄為主，英文翻譯為輔。
雙語字幕生成流程：中文轉錄 → 英文翻譯 → 合併為雙語 SRT/ASS。

## Ecosystem Overview

| 工具 | 語言 | 速度 | VRAM 需求 | 適用場景 |
|------|------|------|-----------|---------|
| OpenAI Whisper | Python | 基準 | 高 | 研究、原型開發 |
| whisper.cpp | C/C++ | 2-4x | 依模型與後端 | Windows CUDA / CPU 本地推論 |
| faster-whisper | Python | 4x | 低（int8） | 量產、GPU 批次 |
| WhisperX | Python | 4x + 對齊 | 中 | 需要逐字時間戳、說話者標記 |

## Model Selection

| 模型 | 磁碟 | VRAM | 速度 | 準確度 | 建議用途 |
|------|------|------|------|--------|---------|
| tiny | 75MB | ~1GB | 最快 | 低 | 測試、即時 |
| base | 142MB | ~1GB | 快 | 中等 | 快速草稿 |
| small | 466MB | ~2GB | 中等 | 良好 | 輕量日常使用 |
| medium | 1.5GB | ~5GB | 慢 | 高 | 高品質需求 |
| large-v3 | 2.9GB | ~10GB | 最慢 | 最佳 | 最高精確度 |
| large-v3-turbo | ~1.5GB | ~6GB | 快 | 接近 large-v3 | **本專案預設** |

## Method 1: OpenAI Whisper（Python）

### Installation

```powershell
pip install openai-whisper
```

### Transcribe to SRT

```powershell
# 基本轉錄（自動偵測語言）
whisper input.mp4 --model small --output_format srt

# 指定繁體中文（更快更準確 — 預設）
whisper input.mp4 --model small --language zh --output_format srt

# 中文轉錄 + 英文翻譯（雙語字幕基礎）
whisper input.mp4 --model small --language zh --task transcribe --output_format srt --output_dir output/zh
whisper input.mp4 --model small --language zh --task translate --output_format srt --output_dir output/en

# 輸出多種格式
whisper input.mp4 --model medium --output_format all

# 翻譯成英文（非中文語音 → 英文字幕）
whisper input.mp4 --model small --task translate --output_format srt
```

## Method 2: Whisper.cpp（C/C++）

### Installation（Windows，全域目前使用者）

```powershell
# 安裝官方 whisper.cpp CUDA 12.4 x64、CPU 回退版與 large-v3-turbo
pwsh -File scripts/install-whisper-cpp.ps1

# 請開啟新終端；全域命令與預設模型環境變數會生效
whisper-cli --version
whisper-cli -m $env:WHISPER_CPP_MODEL --help
```

### Usage

```powershell
# 專案 wrapper 接受影片或音訊；影片會自動抽成 16 kHz mono WAV
pwsh -File scripts/whisper-cli.ps1 input.mp4 -Language zh -OutputPrefix output/zh/input

# 中文語音翻譯成英文 SRT
pwsh -File scripts/whisper-cli.ps1 input.mp4 -Language zh -Task translate -OutputPrefix output/en/input

# CPU 回退或輸出 VTT
pwsh -File scripts/whisper-cli.ps1 audio.wav -Language auto -Format vtt -Cpu -OutputPrefix output/audio

# 直接呼叫全域 CLI 時，必須傳入模型路徑
whisper-cli -m $env:WHISPER_CPP_MODEL -f audio.wav -l zh --output-srt -of output/audio
```

安裝位置預設為 `%LOCALAPPDATA%\whisper.cpp`。`bin` 會加入目前使用者的
`PATH`，模型路徑則寫入使用者環境變數 `WHISPER_CPP_MODEL`。

### 本機全域安裝與驗證基線

目前 Windows 使用者的已驗證安裝：

| 項目 | 值 |
|------|----|
| whisper.cpp | `v1.9.1` |
| CUDA runtime | 官方 CUDA 12.4 x64 release |
| GPU | NVIDIA GeForce RTX 3070 Ti，8 GB VRAM |
| CPU 回退 | 官方 Windows x64 release |
| 模型 | multilingual `ggml-large-v3-turbo.bin`，非量化 |
| CLI | `%LOCALAPPDATA%\whisper.cpp\bin\whisper-cli.exe` |
| CPU CLI | `%LOCALAPPDATA%\whisper.cpp\cpu-bin\whisper-cli.exe` |
| 模型路徑 | `%LOCALAPPDATA%\whisper.cpp\models\ggml-large-v3-turbo.bin` |

官方檔案完整性基線：

```text
whisper-bin-x64.zip
SHA256 7D8BE46ECD31828E1EB7A2ECDD0D6B314FEAFD82163038AB6092594B0A063539

whisper-cublas-12.4.0-bin-x64.zip
SHA256 106A2030EFF8998E4EF320FE72E263A78449E9040386EE27C41EA80B001B601B

ggml-large-v3-turbo.bin
SHA256 1FC70F774D38EB169993AC391EEA357EF47C88757EF72EE5943879B7E8E2BC69
```

安裝完成後需開啟新終端，再驗證全域命令與模型：

```powershell
whisper-cli --version
Get-Command whisper-cli
Test-Path $env:WHISPER_CPP_MODEL
Get-FileHash -Algorithm SHA256 $env:WHISPER_CPP_MODEL
```

已使用 5.7 秒英文語音完成實際 CUDA 轉錄；`large-v3-turbo` 正確建立 SRT，
當次總處理時間約 2.1 秒。效能數字只代表該次短音訊 smoke test，長影片仍需
依內容、分段、溫度與 GPU 負載重新量測。

若 CUDA 初始化失敗，先確認日誌與 NVIDIA 驅動；需要立即完成工作時，使用：

```powershell
pwsh -File scripts/whisper-cli.ps1 input.mp4 -Language zh -Cpu -OutputPrefix output/input_cpu
```

不要因 CUDA 失敗而宣稱 GPU 驗證通過；回報時應區分 CUDA、CPU、模型載入及
實際字幕輸出四項證據。

## Method 3: Faster-Whisper（Python，推薦）

### Installation

```powershell
pip install faster-whisper
```

### Python Script — Bilingual Transcription（zh-TW + EN）

```python
# transcribe_bilingual.py — Generate zh-TW + EN bilingual subtitles
from faster_whisper import WhisperModel

model = WhisperModel("small", device="cuda", compute_type="float16")

# Step 1: Transcribe Chinese (zh)
segments_zh, info = model.transcribe("audio.wav", beam_size=5, language="zh")
print(f"Chinese: detected {info.language} (p={info.language_probability:.2f})")

# Step 2: Translate to English (zh → en)
segments_en, _ = model.transcribe("audio.wav", beam_size=5, language="zh", task="translate")

def write_srt(segments, path):
    with open(path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            s = f"{int(seg.start//3600):02d}:{int(seg.start%3600//60):02d}:{seg.start%60:06.3f}".replace(".", ",")
            e = f"{int(seg.end//3600):02d}:{int(seg.end%3600//60):02d}:{seg.end%60:06.3f}".replace(".", ",")
            f.write(f"{i}\n{s} --> {e}\n{seg.text.strip()}\n\n")

# Write separate SRT files
write_srt(segments_zh, "output.zh.srt")
write_srt(segments_en, "output.en.srt")
print("Bilingual SRTs saved: output.zh.srt, output.en.srt")

# Step 3: Merge into bilingual SRT (zh-TW main line, EN second line)
def merge_bilingual(zh_path, en_path, out_path):
    def load_srt(p):
        with open(p, 'r', encoding='utf-8') as f:
            blocks = f.read().strip().split('\n\n')
        return [b for b in blocks if b.count('\n') >= 2]

    zh_blocks = load_srt(zh_path)
    en_blocks = load_srt(en_path)

    with open(out_path, 'w', encoding='utf-8') as f:
        for i, (zh, en) in enumerate(zip(zh_blocks, en_blocks), 1):
            zh_lines = zh.split('\n')
            en_lines = en.split('\n')
            # zh-TW line 1, EN line 2, same timestamp
            time_range = zh_lines[1]  # Use zh-TW timestamp
            zh_text = '\n'.join(zh_lines[2:])
            en_text = '\n'.join(en_lines[2:])
            f.write(f"{i}\n{time_range}\n{zh_text}\n{en_text}\n\n")

merge_bilingual("output.zh.srt", "output.en.srt", "output.bilingual.srt")
print("Merged bilingual SRT: output.bilingual.srt")
```

### Batch Processing

```python
# batch_transcribe.py
import os
from faster_whisper import WhisperModel

model = WhisperModel("medium", device="cuda", compute_type="float16")

input_dir = "videos/"
output_dir = "subtitles/"
os.makedirs(output_dir, exist_ok=True)

for file in os.listdir(input_dir):
    if file.lower().endswith(('.mp4', '.mkv', '.mov', '.avi')):
        video_path = os.path.join(input_dir, file)
        audio_path = os.path.join(output_dir, f"{os.path.splitext(file)[0]}.wav")
        srt_path = os.path.join(output_dir, f"{os.path.splitext(file)[0]}.srt")

        # 提取音訊
        os.system(f'ffmpeg -i "{video_path}" -vn -acodec pcm_s16le -ar 16000 -ac 1 "{audio_path}" -y')

        # 轉錄
        segments, _ = model.transcribe(audio_path, beam_size=5)

        # 寫入 SRT
        with open(srt_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, 1):
                start = seg.start
                end = seg.end
                f.write(f"{i}\n{fmt_time(start)} --> {fmt_time(end)}\n{seg.text.strip()}\n\n")

        # 清理暫存
        os.remove(audio_path)

        print(f"Done: {file} -> {srt_path}")

def fmt_time(seconds):
    h = int(seconds // 3600)
    m = int(seconds % 3600 // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")
```

## Full Pipeline: Video → Bilingual Subtitled Video（zh-TW + EN）

### Windows PowerShell 腳本

```powershell
# auto-subtitle-bilingual.ps1 — Generate zh-TW + EN bilingual subtitles
param(
    [Parameter(Mandatory=$true)]
    [string]$InputVideo,
    [string]$ModelPath = $env:WHISPER_CPP_MODEL,
    [string]$OutputDir = ".",
    [switch]$AssFormat  # Use ASS format for different font sizes
)

$name = [System.IO.Path]::GetFileNameWithoutExtension($InputVideo)
$audioFile = Join-Path $OutputDir "$name.wav"
$zhSrtFile = Join-Path $OutputDir "$name.zh.srt"
$enSrtFile = Join-Path $OutputDir "$name.en.srt"
$bilingualFile = Join-Path $OutputDir "$name.bilingual.srt"
$outputVideo = Join-Path $OutputDir "${name}_subtitled.mp4"

Write-Host "Step 1: Extracting audio..."
ffmpeg -i $InputVideo -vn -acodec pcm_s16le -ar 16000 -ac 1 $audioFile -y

Write-Host "Step 2: Transcribing Chinese (zh)..."
& scripts/whisper-cli.ps1 $audioFile -ModelPath $ModelPath -Language zh -Task transcribe `
    -OutputPrefix ([System.IO.Path]::ChangeExtension($zhSrtFile, $null))

Write-Host "Step 3: Translating to English..."
& scripts/whisper-cli.ps1 $audioFile -ModelPath $ModelPath -Language zh -Task translate `
    -OutputPrefix ([System.IO.Path]::ChangeExtension($enSrtFile, $null))

Write-Host "Step 4: Merging bilingual subtitles..."
if ($AssFormat) {
    # ASS format: auto-detect video height for dynamic font scaling
    $videoH = & ffprobe -v error -select_streams v:0 -show_entries stream=height -of default=noprint_wrappers=1:nokey=1 $InputVideo 2>&1
    python scripts/generate_bilingual_ass.py $zhSrtFile $enSrtFile (Join-Path $OutputDir "$name.bilingual.ass") --background none --video-height $videoH
    $subtitleFilter = "ass=" + (Join-Path $OutputDir "$name.bilingual.ass")
} else {
    # Merged SRT: Chinese line 1, English line 2 (uniform style)
    python scripts/merge_bilingual_srt.py $zhSrtFile $enSrtFile $bilingualFile
    $subtitleFilter = "subtitles=$bilingualFile:force_style='FontName=Noto Sans TC,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=50,BorderStyle=1'"
}

Write-Host "Step 5: Burning bilingual subtitles into video..."
ffmpeg -i $InputVideo -vf $subtitleFilter -c:v libx264 -crf 23 -c:a aac $outputVideo -y

Write-Host "Done! Bilingual subtitled video saved to: $outputVideo"
Write-Host "Intermediate audio and subtitle files were preserved in: $OutputDir"
```

## Quality Optimization Tips

1. **音訊預處理**：先降噪再轉錄可顯著提升準確度
   ```powershell
   ffmpeg -i input.mp4 -vn -af "anlmdn=10" -ar 16000 -ac 1 audio_denoised.wav
   ```

2. **語言指定**：指定語言可提升準確度並加速。預設為繁體中文：
   ```powershell
   pwsh -File scripts/whisper-cli.ps1 audio.wav -Language zh -OutputPrefix output/audio
   ```

3. **雙語字幕品質關鍵**：
   - 中文轉錄使用 `--task transcribe`、英文使用 `--task translate`
   - 兩個指令使用相同的 `--language zh` 參數確保一致性
   - 產生的兩份 SRT 時間軸可能略有差異，建議使用 ASS 格式以分別控制樣式

4. **段落長度控制**：Whisper 預設段落較長，可後處理分割
   ```powershell
   # 建議使用 Python 後處理腳本
   ```

5. **雙語字數限制**：每行中文建議不超過 36 字元，英文不超過 42 字元，雙語合計最多 4 行

## Verification

```powershell
# 檢查 SRT 內容
Get-Content output.srt -Encoding UTF8 | Select-Object -First 20

# 檢查字幕時間軸
python -c "
import re
with open('output.srt', 'r', encoding='utf-8') as f:
    content = f.read()
times = re.findall(r'(\d+:\d+:\d+,\d+) --> (\d+:\d+:\d+,\d+)', content)
print(f'Total subtitle entries: {len(times)}')
for t in times[:5]:
    print(f'{t[0]} -> {t[1]}')
"
```
