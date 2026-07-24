# Auto Editing — Jump Cut Techniques

## Overview

跳剪（Jump Cut）是將影片中不必要的段落移除，讓內容更緊湊的編輯技術。
本文件涵蓋自動化跳剪的各種實現方式與最佳實踐。

## Tool: jumpcutter（Python）

自動偵測靜音並跳剪的 Python 工具。

### Installation & Usage

```powershell
pip install jumpcutter

# 基本用法
jumpcutter -i input.mp4 -o output.mp4

# 進階參數
jumpcutter -i input.mp4 -o output.mp4 -m 0.05 -d 1.0 -f 0.2 -s 0.2 -x 2000 -l 1.0
```

### Parameters

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `-m, --min_silence_len` | 0.05 | 最短靜音長度（秒） |
| `-d, --silence_db` | 1.0 | 靜音判定閾值（dB） |
| `-f, --frame_rate` | 0.2 | 音訊取樣間隔（秒） |
| `-s, --silence_threshold` | 0.2 | 靜音音量閾值 |
| `-x, --chunk_size` | 2000 | 處理區塊大小（毫秒） |
| `-l, --min_loud_part_duration` | 1.0 | 最短保留段落（秒） |
| `-c, --cut` | silent | 剪輯模式（silent/voiced/both） |

## Advanced: Auto-Editor Jump Cut Pipeline

auto-editor 支援更精細的跳剪控制，包含不同段落的速度調整。

### 混合速度跳剪

```powershell
# 非靜音 1.5x 加速，靜音剪掉
auto-editor input.mp4 --edit audio:threshold:-20dB --when:inactive speed:1.5 --output output.mp4

# 不同速度層級
auto-editor input.mp4 --edit audio:threshold:-20dB --when:inactive speed:2.0 --when:active speed:1.2 --output output.mp4
```

### 以時間範圍為基礎

```powershell
# 前 30 秒保持原速，之後套用跳剪
auto-editor input.mp4 --edit audio:threshold:-20dB --ignore-before 30 --output output.mp4
```

## Workflow: Content-Aware Jump Cut

結合 Whisper 語音辨識 + auto-editor 的智慧跳剪。

```powershell
# Step 1: 產生字幕（同時獲得語音時間軸）
whisper input.mp4 --model small --output_format srt

# Step 2: 使用 auto-editor 移除靜音
auto-editor input.mp4 --edit audio:threshold:-25dB --output jumpcut.mp4

# Step 3: 根據字幕重新調整時間軸（Python 腳本）
python -c "
import re

# 讀取 SRT，找出過長的無字幕段落
def find_long_gaps(srt_path, max_gap=3.0):
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析時間戳
    pattern = r'(\d+:\d+:\d+,\d+) --> (\d+:\d+:\d+,\d+)'
    matches = re.findall(pattern, content)

    def ts_to_sec(ts):
        h, m, s = ts.replace(',', '.').split(':')
        return int(h)*3600 + int(m)*60 + float(s)

    gaps = []
    for i in range(len(matches)-1):
        end_curr = ts_to_sec(matches[i][1])
        start_next = ts_to_sec(matches[i+1][0])
        gap = start_next - end_curr
        if gap > max_gap:
            gaps.append((end_curr, start_next, gap))

    return gaps

gaps = find_long_gaps('input.srt')
for g in gaps:
    print(f'Gap: {g[0]:.1f}s -> {g[1]:.1f}s ({g[2]:.1f}s)')
"
```

## Common Issues & Solutions

| 問題 | 原因 | 解決方案 |
|------|------|---------|
| 跳剪太突兀 | 剪輯點不自然 | 提高靜音閾值或增加最小段落長度 |
| 重要內容被剪掉 | 閾值太低 | 調高 `threshold` 或 `min-loud` |
| 跳剪後影音不同步 | 剪輯錯誤 | 使用 `-c:v copy` 無法跳剪，必須重新編碼 |
| 跳剪後檔案過大 | 重新編碼 | 提高 CRF 值（如 28）以減小檔案 |

## Best Practices

1. **先看再剪**：先用 auto-editor 的 `--export clip-sequence` 輸出剪輯段落
2. **保留潤飾空間**：不要一次剪太多，保留 10-20% 的緩衝
3. **語速考量**：快速說話者可用較短的最小靜音長度，慢速說話者反之
4. **音樂內容**：純音樂影片不適合跳剪，應改用章節標記
