# Workflow — Full Production Pipeline

## Purpose

由目前 Codex／Agent 編排完整影片產線：

1. 取得或檢查來源影片。
2. 預覽並核准 Auto-Editor 設定。
3. 完成剪輯後，以 whisper.cpp 產生原文 SRT。
4. 需要雙語字幕時，由目前 Agent 直接翻譯 SRT。
5. 需要旁白時，以 qwentts.cpp 合成，再用 whisper.cpp 回聽。
6. 由目前 Agent 翻譯旁白回聽 SRT。
7. 合併字幕、混音、燒錄並驗收。

這是 **Agent 編排流程**，不是一個可脫離 Agent 連續執行的 PowerShell
巨型腳本。PowerShell、qwentts.cpp、whisper.cpp 與 FFmpeg 都不能自行呼叫
目前 Agent 的語言能力；Agent 必須在標示的翻譯步驟實際讀寫 SRT。

## Prompt

```text
使用 youtube-video-editor 處理 <input.mp4>：
- 先用 Balanced 預覽 Auto-Editor，確認後再剪輯。
- 使用 qwentts.cpp 與已授權的 <reference.wav>/<reference.txt> 產生中文旁白。
- whisper.cpp large-v3-turbo 只做中文辨識與旁白回聽。
- 你直接將 SRT 翻成英文；不使用 OpenAI API、外部翻譯服務或 Whisper translate。
- 保留每個 cue 的序號與時間碼，驗證後產生雙語字幕。
- 加入 <bgm.mp3>，旁白出現時自動壓低原音，最後輸出 MP4。
```

## Agent execution contract

- 使用絕對路徑並建立本次任務專用工作目錄。
- 不覆寫既有輸出；需要重跑時建立新路徑，或明確使用安全備份參數。
- 每個 native command 後檢查 `$LASTEXITCODE`，並確認輸出是非空檔案。
- Auto-Editor 先 `Preview`；只有使用者已核准時才 `Render`。
- 先完成剪輯，再產生交付字幕，避免時間軸失配。
- whisper.cpp 一律 `transcribe`；不得傳入 `-Task translate`、`--translate` 或 `-tr`。
- Agent 翻譯只改 cue 文字，不改序號、時間碼、cue 數量或區塊順序。
- 任一必要字幕、旁白、混音或驗證失敗時停止，不發布降級成品。

## 1. Preflight

```powershell
Set-Location E:\youtube_videos_editor

$input = "D:\video\input.mp4"
$work = "D:\video\work\job-001"
$edited = Join-Path $work "edited.mp4"
$audio = Join-Path $work "edited.wav"
$zhSrt = Join-Path $work "edited.zh.srt"
$enSrt = Join-Path $work "edited.en.srt"
$bilingualSrt = Join-Path $work "edited.bilingual.srt"
$final = "D:\video\output\final.mp4"

New-Item -ItemType Directory -Force -Path $work | Out-Null
if (Test-Path -LiteralPath $final) {
    throw "Final output already exists; choose a new path: $final"
}
pwsh -NoLogo -NoProfile -File .\scripts\check-dependencies.ps1
if ($LASTEXITCODE -ne 0) { throw "Dependency preflight failed." }
```

## 2. Auto-Editor

```powershell
pwsh -NoLogo -NoProfile -File .\scripts\auto-edit.ps1 `
  -InputPath $input -Profile Balanced -Mode Preview
if ($LASTEXITCODE -ne 0) { throw "Auto-Editor preview failed." }

# Agent waits for explicit approval before Render.
pwsh -NoLogo -NoProfile -File .\scripts\auto-edit.ps1 `
  -InputPath $input -OutputPath $edited -Profile Balanced -Mode Render
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $edited -PathType Leaf)) {
    throw "Auto-Editor render failed."
}
```

## 3. Source transcription

```powershell
ffmpeg -hide_banner -loglevel error -i $edited -vn -acodec pcm_s16le `
  -ar 16000 -ac 1 -y $audio
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $audio -PathType Leaf)) {
    throw "Audio extraction failed."
}

pwsh -NoLogo -NoProfile -File .\scripts\whisper-cli.ps1 $audio `
  -Language zh -Task transcribe `
  -OutputPrefix ([IO.Path]::ChangeExtension($zhSrt, $null))
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $zhSrt -PathType Leaf)) {
    throw "Whisper transcription failed."
}
```

## 4. Active Agent translation

此步驟由目前 Agent 本身完成：

1. 以 UTF-8 讀取 `$zhSrt`。
2. 將每個 cue 的文字翻成自然英文。
3. 以 UTF-8 寫入 `$enSrt`，不加入前言、Markdown fence 或註解。
4. 執行嚴格驗證器。

```powershell
python .\scripts\validate_agent_translation.py $zhSrt $enSrt
if ($LASTEXITCODE -ne 0) { throw "Agent translation validation failed." }

python .\scripts\merge_bilingual_srt.py $zhSrt $enSrt $bilingualSrt
if ($LASTEXITCODE -ne 0 -or
    -not (Test-Path -LiteralPath $bilingualSrt -PathType Leaf)) {
    throw "Bilingual subtitle merge failed."
}
```

需要不同中英文字級時，改用：

```powershell
$ass = Join-Path $work "edited.bilingual.ass"
python .\scripts\generate_bilingual_ass.py $zhSrt $enSrt $ass `
  --background none --video-height 1080
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $ass -PathType Leaf)) {
    throw "Bilingual ASS generation failed."
}
```

## 5. Authorized Qwen narration

```powershell
$narration = Join-Path $work "narration.wav"
$narrationAsr = Join-Path $work "narration.asr.srt"
$narrationEn = Join-Path $work "narration.en.srt"

pwsh -NoLogo -NoProfile -File .\scripts\qwen-narration-pipeline.ps1 `
  -TextFile "D:\video\narration.txt" `
  -ReferenceWav "D:\voice\reference.wav" `
  -ReferenceTextFile "D:\voice\reference.txt" `
  -OutputPath $narration `
  -QwenLanguage Chinese -WhisperLanguage zh `
  -ConfirmVoiceRights
if ($LASTEXITCODE -ne 0 -or
    -not (Test-Path -LiteralPath $narration -PathType Leaf) -or
    -not (Test-Path -LiteralPath $narrationAsr -PathType Leaf)) {
    throw "Narration pipeline failed."
}
```

目前 Agent 接著讀取 `$narrationAsr`，翻譯 cue 文字並寫入 `$narrationEn`：

```powershell
python .\scripts\validate_agent_translation.py $narrationAsr $narrationEn
if ($LASTEXITCODE -ne 0) { throw "Narration translation validation failed." }
```

## 6. Audio mixing

無 BGM 時，input `0` 是影片、input `1` 是旁白：

```powershell
$mixed = Join-Path $work "mixed.mp4"
ffmpeg -hide_banner -loglevel error -i $edited -i $narration `
  -filter_complex "[1:a]adelay=2000|2000[narration];[0:a][narration]sidechaincompress=threshold=0.015:ratio=10:attack=100:release=500[ducked];[ducked][narration]amix=inputs=2:duration=first[aout]" `
  -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k -y $mixed
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $mixed -PathType Leaf)) {
    throw "Narration mix failed."
}
```

有 BGM 時，input `2` 是 BGM，並明確映射 `[aout]`：

```powershell
$bgm = "D:\music\bgm.mp3"
ffmpeg -hide_banner -loglevel error -i $edited -i $narration -i $bgm `
  -filter_complex "[1:a]adelay=2000|2000[narration];[0:a][narration]sidechaincompress=threshold=0.015:ratio=10:attack=100:release=500[ducked];[ducked][narration]amix=inputs=2:duration=first[mix1];[2:a]volume=0.12[bgm];[mix1][bgm]amix=inputs=2:duration=first[aout]" `
  -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k -y $mixed
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $mixed -PathType Leaf)) {
    throw "Narration and BGM mix failed."
}
```

## 7. Burn subtitles and verify

```powershell
$escapedSrt = $bilingualSrt.Replace("\", "/").Replace(":", "\:")
ffmpeg -hide_banner -loglevel error -i $mixed `
  -vf "subtitles='$escapedSrt':force_style='FontName=Noto Sans TC,FontSize=22,Outline=2,Shadow=1,MarginV=50'" `
  -c:v libx264 -crf 23 -c:a copy -n $final
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $final -PathType Leaf)) {
    throw "Subtitle burn failed."
}

pwsh -NoLogo -NoProfile -File .\scripts\validate.ps1 `
  -VideoPath $final -SrtPath $bilingualSrt -OutputPath $final
if ($LASTEXITCODE -ne 0) { throw "Final validation failed." }
```

最後由 Agent 實際檢查：

- 完整播放與抽查畫面，確認影音同步、字幕可讀性、旁白無爆音或截斷。
- 對照旁白稿與 `.asr.srt`，檢查人名、數字與專有名詞。
- 人工覆核英文語意；結構驗證不等於翻譯品質驗證。
- 回報實際 backend、輸出路徑、時長、解析度、測試結果與剩餘風險。
