# Workflow — Batch Processing

## Purpose

由目前 Codex／Agent 批次處理多部影片。Agent 對每個檔案依序執行：

`Auto-Editor → Whisper 原文 SRT → Agent 翻譯 → 驗證 → 旁白 → 混音 → 輸出`

不要嘗試讓一個獨立 PowerShell 迴圈在執行途中「呼叫 Agent 翻譯」；Agent 應在
每個檔案的工具呼叫之間直接讀取並翻譯 SRT。這能維持 fail-closed，也不需要
容易漂移的 Prepare/Finalize manifest 或重跑旗標。

## Prompt

```text
使用 youtube-video-editor 批次處理 D:\raw 內的 MP4。
先以第一部影片預覽 Balanced Auto-Editor；我核准後才處理全部檔案。
每部影片用 whisper.cpp large-v3-turbo 轉錄中文，再由你直接翻譯英文 SRT。
不要使用 OpenAI API、外部翻譯服務或 Whisper translate。
每部影片驗證字幕結構後才合併雙語字幕；任何必要階段失敗就把該檔標記失敗，
不得輸出或回報降級成品。每部影片都要附輸出與驗證結果。
```

## Agent execution contract

- 先列出精確輸入清單與預定輸出；不要遞迴掃描未授權目錄。
- 先用代表影片預覽 Auto-Editor；取得核准後才進行批次 Render。
- 每部影片使用獨立工作目錄，避免同名暫存檔與平行競態。
- 目前 Agent 直接翻譯 SRT；只改 cue 文字，保留 cue 數量、序號與時間碼。
- 每個 native command 檢查 `$LASTEXITCODE` 與非空輸出。
- 單檔失敗可繼續下一檔，但 `$failed` 必須增加，且不能留下「成功」成品。
- 預設序列處理 GPU 工作；只有量測 VRAM 足夠時才提高並行度。

## 1. Inventory and representative preview

```powershell
Set-Location E:\youtube_videos_editor
$inputDir = "D:\raw"
$outputDir = "D:\processed"
$files = @(Get-ChildItem -LiteralPath $inputDir -Filter *.mp4 -File)
if ($files.Count -eq 0) { throw "No input MP4 files found." }

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
pwsh -NoLogo -NoProfile -File .\scripts\check-dependencies.ps1
if ($LASTEXITCODE -ne 0) { throw "Dependency preflight failed." }

pwsh -NoLogo -NoProfile -File .\scripts\auto-edit.ps1 `
  -InputPath $files[0].FullName -Profile Balanced -Mode Preview
if ($LASTEXITCODE -ne 0) { throw "Representative preview failed." }
```

Agent 在這裡等待使用者核准。核准後，逐檔執行以下階段。

## 2. Per-file workspace and Auto-Editor

```powershell
$base = [IO.Path]::GetFileNameWithoutExtension($file.Name)
$work = Join-Path $outputDir ("work-" + $base)
$edited = Join-Path $work "edited.mp4"
$audio = Join-Path $work "edited.wav"
$zhSrt = Join-Path $work "edited.zh.srt"
$enSrt = Join-Path $work "edited.en.srt"
$bilingualSrt = Join-Path $work "edited.bilingual.srt"
$output = Join-Path $outputDir ($base + "-processed.mp4")
New-Item -ItemType Directory -Force -Path $work | Out-Null
if (Test-Path -LiteralPath $output) {
    throw "Final output already exists; choose a new path: $output"
}

pwsh -NoLogo -NoProfile -File .\scripts\auto-edit.ps1 `
  -InputPath $file.FullName -OutputPath $edited `
  -Profile Balanced -Mode Render
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $edited -PathType Leaf)) {
    throw "Auto-Editor failed for $($file.FullName)."
}
```

## 3. Whisper transcription and Agent translation

```powershell
ffmpeg -hide_banner -loglevel error -i $edited -vn -acodec pcm_s16le `
  -ar 16000 -ac 1 -y $audio
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $audio -PathType Leaf)) {
    throw "Audio extraction failed for $($file.FullName)."
}

pwsh -NoLogo -NoProfile -File .\scripts\whisper-cli.ps1 $audio `
  -Language zh -Task transcribe `
  -OutputPrefix ([IO.Path]::ChangeExtension($zhSrt, $null))
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $zhSrt -PathType Leaf)) {
    throw "Whisper transcription failed for $($file.FullName)."
}
```

目前 Agent 接著：

1. 讀取 `$zhSrt`。
2. 直接翻譯每個 cue 的文字。
3. 寫入 `$enSrt`，不加入 Markdown 或解說。
4. 驗證後才合併。

```powershell
python .\scripts\validate_agent_translation.py $zhSrt $enSrt
if ($LASTEXITCODE -ne 0) { throw "Agent translation validation failed." }

python .\scripts\merge_bilingual_srt.py $zhSrt $enSrt $bilingualSrt
if ($LASTEXITCODE -ne 0 -or
    -not (Test-Path -LiteralPath $bilingualSrt -PathType Leaf)) {
    throw "Bilingual subtitle merge failed."
}
```

## 4. Optional Qwen narration

每部影片使用對應的 `<basename>.txt` 旁白稿。參考聲音只能使用本人聲音或明確
授權素材。

```powershell
$narrationScript = Join-Path "D:\narration-scripts" ($base + ".txt")
$narration = Join-Path $work "narration.wav"
$narrationAsr = Join-Path $work "narration.asr.srt"
$narrationEn = Join-Path $work "narration.en.srt"

pwsh -NoLogo -NoProfile -File .\scripts\qwen-narration-pipeline.ps1 `
  -TextFile $narrationScript `
  -ReferenceWav "D:\voice\reference.wav" `
  -ReferenceTextFile "D:\voice\reference.txt" `
  -OutputPath $narration `
  -QwenLanguage Chinese -WhisperLanguage zh `
  -ConfirmVoiceRights
if ($LASTEXITCODE -ne 0 -or
    -not (Test-Path -LiteralPath $narration -PathType Leaf) -or
    -not (Test-Path -LiteralPath $narrationAsr -PathType Leaf)) {
    throw "Narration pipeline failed for $($file.FullName)."
}
```

Agent 翻譯 `$narrationAsr` 成 `$narrationEn` 後：

```powershell
python .\scripts\validate_agent_translation.py $narrationAsr $narrationEn
if ($LASTEXITCODE -ne 0) { throw "Narration translation validation failed." }
```

## 5. Correct FFmpeg input mapping

不要以 PowerShell 陣列元素數量推算 FFmpeg input index。明確固定：

- `0`：剪輯後影片
- `1`：旁白
- `2`：BGM（有提供時）

旁白、BGM 與原音三層混音：

```powershell
$bgm = "D:\music\bgm.mp3"
$mixed = Join-Path $work "mixed.mp4"
ffmpeg -hide_banner -loglevel error -i $edited -i $narration -i $bgm `
  -filter_complex "[1:a]adelay=2000|2000[narration];[0:a][narration]sidechaincompress=threshold=0.015:ratio=10:attack=100:release=500[ducked];[ducked][narration]amix=inputs=2:duration=first[mix1];[2:a]volume=0.12[bgm];[mix1][bgm]amix=inputs=2:duration=first[aout]" `
  -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k -y $mixed
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $mixed -PathType Leaf)) {
    throw "Audio mixing failed for $($file.FullName)."
}
```

只有旁白時仍明確映射 `[aout]`：

```powershell
ffmpeg -hide_banner -loglevel error -i $edited -i $narration `
  -filter_complex "[1:a]adelay=2000|2000[narration];[0:a][narration]sidechaincompress=threshold=0.015:ratio=10:attack=100:release=500[ducked];[ducked][narration]amix=inputs=2:duration=first[aout]" `
  -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k -y $mixed
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $mixed -PathType Leaf)) {
    throw "Narration mixing failed for $($file.FullName)."
}
```

## 6. Burn subtitles and record result

```powershell
$escapedSrt = $bilingualSrt.Replace("\", "/").Replace(":", "\:")
ffmpeg -hide_banner -loglevel error -i $mixed `
  -vf "subtitles='$escapedSrt':force_style='FontName=Noto Sans TC,FontSize=22,Outline=2,Shadow=1,MarginV=50'" `
  -c:v libx264 -crf 23 -c:a copy -n $output
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $output -PathType Leaf)) {
    throw "Final render failed for $($file.FullName)."
}
```

Agent 為每個檔案保存結果：

```text
input: absolute source path
output: absolute final path
status: passed | failed
stages: auto-edit, asr, agent-translation, narration, mix, render
duration: input/output seconds
notes: backend, warnings, semantic review
```

只有所有必要階段與最終播放檢查通過，該檔才能計入 `processed`。失敗檔計入
`failed`，保留工作目錄與錯誤證據，繼續下一檔。
