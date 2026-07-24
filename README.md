# YouTube Video Editor Skill

給 OpenAI Codex Desktop／CLI 使用的影片編輯技能。整合 FFmpeg、Auto-Editor、
whisper.cpp、qwentts.cpp、yt-dlp 與 PowerShell／Python wrapper，可完成剪輯、雙語字幕、
字幕燒錄、背景音樂、授權語音複製旁白、Whisper 回聽、Agent 翻譯、縮圖及批次處理。

> English: A Codex skill for reproducible video editing, multilingual subtitles,
> Whisper transcription, Agent-authored translation, authorized Qwen3-TTS narration and
> FFmpeg-based production workflows.

## 在 Codex 中安裝

Windows PowerShell：

```powershell
git clone https://github.com/stevenke1981/youtube-video-editor-skill.git `
  "$HOME\.codex\skills\youtube-video-editor"
```

如需同時提供給其他支援 `.agents/skills` 的 agent：

```powershell
git clone https://github.com/stevenke1981/youtube-video-editor-skill.git `
  "$HOME\.agents\skills\youtube-video-editor"
```

重新啟動 Codex 後，在提示詞中明確寫出：

```text
使用 $youtube-video-editor
```

一般 ChatGPT 網頁版不會自動讀取電腦上的 Codex 技能。若不是使用 Codex
Desktop／CLI，請附上輸入檔及需求，或把本 repo 的 `SKILL.md` 和相關文件加入
可存取的專案工作區。

## 提示詞怎麼寫

建議提供六個欄位：

```text
使用 $youtube-video-editor。

目標：
輸入：
輸出：
處理要求：
限制：
驗收條件：
```

不必指定每一條 FFmpeg 參數；描述成果、素材、限制與如何驗收，讓 Codex
依技能選擇 wrapper、FFmpeg filter 與驗證命令。

### 範例：繁中字幕

```text
使用 $youtube-video-editor。

目標：替影片產生繁體中文字幕並燒錄。
輸入：D:\videos\lesson.mp4
輸出：D:\videos\lesson_subtitled.mp4，另保留 lesson.zh.srt。
處理要求：使用全域 whisper.cpp large-v3-turbo，語言 zh；保留原始影片。
限制：不要覆寫既有檔案，字幕使用 UTF-8。
驗收條件：實際產生 SRT 與影片，用 FFprobe 驗證，抽查至少三個字幕時間點。
```

### 範例：中英雙語字幕

```text
使用 $youtube-video-editor，將 D:\videos\course.mp4 產生繁中與英文雙語字幕。
中文在上、英文在下，使用 ASS 分開控制字級；輸出到 D:\videos\course_bilingual.mp4。
使用 whisper.cpp 只轉錄中文，再由你直接翻譯英文；不要使用 Whisper translate 或
OpenAI API。不覆寫原檔，完成後驗證影音與字幕時間軸。
```

### 範例：授權語音複製旁白

```text
使用 $youtube-video-editor。

目標：使用我已取得授權的參考聲音產生繁中影片旁白。
旁白稿：D:\voice\narration.txt
參考音訊：D:\voice\reference.wav
參考逐字稿：D:\voice\reference.txt
輸出：D:\voice\narration.wav、narration.asr.srt、narration.en.srt
處理要求：使用全域 qwentts.cpp 1.7B Base Q8_0、Language Chinese、seed 42；
合成後用 whisper.cpp large-v3-turbo 回聽辨識中文，再由你直接翻譯成英文 SRT。
限制：不得修改參考音訊，不得覆寫輸出。
驗收條件：確認 CUDA0 與 ICL 啟用，輸出為 24 kHz mono PCM16 WAV，
比較旁白稿與反向 ASR；英文 SRT 必須保留所有 cue 序號與時間碼並通過驗證。
```

只有本人聲音或已取得權利人明確授權的聲音才能用於 voice cloning。對外發布
時應依情境標示 AI 合成，不得用於冒充、詐騙或規避身分驗證。

### 範例：完整影片產線

```text
使用 $youtube-video-editor 處理 D:\raw\episode.mp4：
1. 使用 Auto-Editor Balanced profile 預覽剪輯比例，確認後移除無聲片段。
2. 產生繁中與英文雙語 ASS。
3. 將 D:\assets\bgm.mp3 以不蓋過人聲的音量混入。
4. 輸出 H.264 MP4 到 D:\output\episode-final.mp4。
保留所有中間字幕檔，不覆寫原檔；完成後執行 validate.ps1、FFprobe，
並抽查畫面、字幕和音量。
```

### 範例：只診斷、不修改

```text
使用 $youtube-video-editor 檢查 D:\videos\broken.mp4 為什麼字幕沒有顯示。
只做診斷與回報，不修改檔案；請提供 FFprobe、字幕編碼、filter 路徑與字型檢查證據。
```

## 直接使用 CLI

依賴檢查：

```powershell
pwsh -File scripts/check-dependencies.ps1
```

安裝官方 Auto-Editor 31 binary 與安全 wrapper：

```powershell
pwsh -File scripts/install-auto-editor.ps1
```

先預覽剪輯統計，再渲染：

```powershell
auto-edit -InputPath input.mp4 -Profile Balanced -Mode Preview
auto-edit -InputPath input.mp4 `
  -OutputPath output/input-edited.mp4 `
  -Profile Balanced `
  -Mode Render
```

安裝 whisper.cpp 與 multilingual `large-v3-turbo`：

```powershell
pwsh -File scripts/install-whisper-cpp.ps1
```

影片轉 SRT：

```powershell
pwsh -File scripts/whisper-cli.ps1 input.mp4 `
  -Language zh `
  -OutputPrefix output/input
```

安裝 qwentts.cpp voice-clone runtime：

```powershell
pwsh -File scripts/install-qwentts-cpp.ps1
```

旁白合成與回聽辨識：

```powershell
pwsh -File scripts/qwen-narration-pipeline.ps1 `
  -TextFile narration.txt `
  -ReferenceWav reference.wav `
  -ReferenceTextFile reference.txt `
  -OutputPath output/narration.wav `
  -QwenLanguage Chinese `
  -WhisperLanguage zh `
  -ConfirmVoiceRights
```

成功後建立 `narration.wav` 與 `narration.asr.srt`。接著由目前 Agent 直接翻譯
cue 文字到 `narration.en.srt`，保留序號與時間碼，再執行：

```powershell
python scripts/validate_agent_translation.py `
  output/narration.asr.srt output/narration.en.srt
```

不使用 Whisper `--translate`，也不呼叫 OpenAI API。

## 文件導覽

- [技能入口與品質規則](SKILL.md)
- [whisper.cpp 字幕產線](ai-subtitles/whisper-pipeline.md)
- [Qwen3-TTS 語音複製](ai-subtitles/qwentts-voice-cloning.md)
- [Qwen 旁白、Whisper 回聽與 Agent 翻譯](ai-subtitles/narration.md)
- [Auto-Editor 安全靜音移除](auto-editing/silence-removal.md)
- [Auto-Editor 跳剪策略](auto-editing/jump-cut.md)
- [FFmpeg 基本剪輯](ffmpeg-core/basic-editing.md)
- [字幕與雙語 ASS](ffmpeg-core/subtitles.md)
- [完整產線](workflows/full-pipeline.md)
- [批次處理](workflows/batch-processing.md)

## 驗證

```powershell
python tests/test_skill_scripts.py -v

$env:PYTHONUTF8 = "1"
python "$HOME\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .
```

目前測試涵蓋輸出防覆寫、字幕時間對齊、旁白失敗處理、縮圖、FFmpeg
剪輯 smoke、whisper.cpp wrapper、qwentts.cpp wrapper、Qwen → Whisper 回聽
管線，以及 Agent 翻譯 SRT 的結構驗證。

## 不包含的檔案

本 repo 不提交語音模型、影片、音訊、轉錄輸出、CUDA runtime 或本機
Codebase Memory 索引。安裝器會從官方來源下載模型並驗證 SHA-256。

## 動態字幕與智慧字卡（Dynamic Typography）

### 命令（不覆寫預設）

```powershell
pwsh -File scripts/typography.ps1 plan `
  -InputPath captions.zh-TW.srt `
  -OutputPath "output\demo.plan.json"

pwsh -File scripts/typography.ps1 ass `
  -InputPath "output\demo.plan.json" `
  -OutputPath "output\demo.ass"

pwsh -File scripts/typography.ps1 validate `
  -InputPath "output\demo.plan.json" `
  -OutputPath "output\demo.qa.json"

pwsh -File scripts/typography.ps1 render `
  -InputPath "input.mp4" `
  -PlanPath "output\demo.plan.json" `
  -AssPath "output\demo.ass" `
  -OutputPath "output\demo.typography.mp4"
```

### 依賴檢查

```powershell
pwsh -File scripts/check-dependencies.ps1
```

此子流程會預設檢查 FFmpeg、FFprobe、qwen/whisper/auto-editor 並額外提供 typography 前置（FFmpeg ass/subtitles 檢查）。

實作、契約、範例與測試保留在
[`youtube-video-typography-devpack`](youtube-video-typography-devpack/) 子專案；root
腳本只是薄路由。ASS + FFmpeg MVP 已驗收。Remotion demo renderer 亦已完成
固定版本安裝、測試、typecheck、CLI render 與五張畫面抽查；逐詞 karaoke、
人臉避讓、粒子／貼紙與自動修復仍是 P1／P2，不列為已交付能力。
