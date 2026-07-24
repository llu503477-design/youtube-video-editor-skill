# Qwen3-TTS 旁白、Whisper 回聽與 Agent 翻譯

本技能的旁白預設流程：

```text
旁白稿 + 已授權參考聲音
  → qwentts.cpp 合成 WAV
  → whisper.cpp large-v3-turbo 原語言辨識
  → 執行技能的 Agent 直接翻譯 SRT
  → 驗證序號、時間碼與英文內容
```

`whisper.cpp` 在此只負責辨識。不得使用 `--translate`，不得呼叫 OpenAI API，
也不需要 `OPENAI_API_KEY`。翻譯是目前執行任務的 Codex／Agent 本身完成。

## 前置條件

```powershell
pwsh -File scripts/install-qwentts-cpp.ps1
pwsh -File scripts/install-whisper-cpp.ps1
qwen-tts --help
whisper-cli --version
Test-Path $env:QWENTTS_CPP_MODEL
Test-Path $env:QWENTTS_CPP_CODEC
Test-Path $env:WHISPER_CPP_MODEL
```

需要 UTF-8 旁白稿、清晰的參考 WAV、與參考 WAV 逐字一致的逐字稿，以及聲音
本人或權利人的明確授權。`-ConfirmVoiceRights` 是必要確認，但不替代實際授權。

## 階段一：合成並回聽辨識

```powershell
pwsh -File scripts/qwen-narration-pipeline.ps1 `
  -TextFile D:\video\narration.txt `
  -ReferenceWav D:\voice\reference.wav `
  -ReferenceTextFile D:\voice\reference.txt `
  -OutputPath D:\video\output\narration.wav `
  -QwenLanguage Chinese `
  -WhisperLanguage zh `
  -ConfirmVoiceRights
```

腳本建立兩個成品：

| 輸出 | 用途 |
|---|---|
| `narration.wav` | qwentts.cpp 產生的 24 kHz mono 旁白 |
| `narration.asr.srt` | whisper.cpp large-v3-turbo 原語言回聽 |

Qwen 或 Whisper 任一階段失敗時，不發布部分成品。預設拒絕覆寫；`-Force`
會在新成品全部成功後保留舊檔的時間戳備份。

## 階段二：由 Agent 翻譯

完成前一階段後，Agent 必須：

1. 讀取 `narration.asr.srt`。
2. 只翻譯每個 cue 的文字內容為自然英文。
3. 完整保留 cue 序號、`HH:MM:SS,mmm --> HH:MM:SS,mmm` 時間碼與分段數。
4. 以 UTF-8 寫入同目錄的 `narration.en.srt`。
5. 不呼叫 Whisper translate、OpenAI API 或外部翻譯服務。

翻譯提示可使用：

```text
讀取 narration.asr.srt，由你直接把每個字幕 cue 翻成自然英文。
只翻譯字幕文字，序號、時間碼與 cue 數量必須逐項保持不變。
以 UTF-8 寫入 narration.en.srt；不要呼叫 OpenAI API 或 whisper --translate。
```

完成後執行：

```powershell
python scripts/validate_agent_translation.py `
  output/narration.asr.srt `
  output/narration.en.srt
```

驗證器會拒絕 cue 數量、序號或時間碼被改動，以及內容不是以英文為主的輸出。

## 人工驗收

```powershell
ffprobe -v error -show_entries stream=codec_name,sample_rate,channels `
  -show_entries format=duration -of json output/narration.wav

Get-Content output/narration.asr.srt
Get-Content output/narration.en.srt
```

- 實際聆聽 WAV，確認沒有截斷、爆音或錯誤停頓。
- 對照旁白稿與 `.asr.srt`；專有名詞、人名與數字需人工修訂。
- 檢查 `.en.srt` 語意與術語；結構驗證通過不代表翻譯品質必然正確。
- 另行判斷音色相似度；Whisper 回聽只能驗證內容。

## 混入影片

驗收後再以旁白觸發原始音訊 ducking：

```powershell
ffmpeg -i input.mp4 -i output/narration.wav `
  -filter_complex "[0:a][1:a]sidechaincompress=threshold=0.015:ratio=10:attack=100:release=500[ducked];[ducked][1:a]amix=inputs=2:duration=first[aout]" `
  -map 0:v:0 -map "[aout]" -c:v copy -c:a aac -b:a 192k output/with_narration.mp4
```

## 舊 Edge-TTS 相容模式

只有使用者明確要求 Edge-TTS、分段模板或舊 `intro/full/summary` 行為時，才使用
`scripts/narrate.py`。它不是目前預設的 Qwen → Whisper → Agent 旁白流程。
