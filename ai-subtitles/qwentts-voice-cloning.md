# Qwen3-TTS Voice Cloning — qwentts.cpp

使用 `qwentts.cpp` Base 模型從參考 WAV 複製音色，產生 24 kHz mono WAV。適合
影片旁白、角色配音與同一聲線的批次生成。

## 使用邊界

- 只複製本人聲音，或已取得聲音權利人明確授權的聲音。
- 對外發布時應依情境標示 AI 合成，不得用於冒充、詐騙或規避身分驗證。
- 保留原始參考音訊、逐字稿、模型、seed 與產生命令，以便追溯。

## Windows 全域安裝

```powershell
pwsh -File scripts/install-qwentts-cpp.ps1
```

安裝器固定使用：

| 項目 | 基線 |
|------|------|
| 原始碼 | `ServeurpersoCom/qwentts.cpp` commit `82cd05b9f3a175612dc89fd6943e610fab096ef5` |
| Build | CUDA 13.2、SM 8.6、Release、NVCC host `/utf-8` |
| Talker | `qwen-talker-1.7b-base-Q8_0.gguf` |
| Codec | `qwen-tokenizer-12hz-Q8_0.gguf` |
| CLI | `%LOCALAPPDATA%\qwentts.cpp\bin\qwen-tts.exe` |
| Models | `%LOCALAPPDATA%\qwentts.cpp\models` |

模型完整性：

```text
qwen-talker-1.7b-base-Q8_0.gguf
SHA256 4B9A33A236908DD9435A42F7A396E38038329D053B704342A6413C08544C4FDA

qwen-tokenizer-12hz-Q8_0.gguf
SHA256 1883BEEED99348FC35E23DD225E9082F93F6F8C109330A33D935BAA8ACDBFD94
```

安裝後開啟新終端並驗證：

```powershell
qwen-tts --help
qwen-codec --help
Get-Command qwen-voice-clone
Test-Path $env:QWENTTS_CPP_MODEL
Test-Path $env:QWENTTS_CPP_CODEC
```

使用者環境變數：

- `QWENTTS_CPP_EXE`
- `QWENTTS_CPP_MODEL`
- `QWENTTS_CPP_CODEC`
- `QWENTTS_CPP_SOURCE_COMMIT`

## 參考音訊準備

建議使用 5–15 秒、單一說話者、無背景音樂、無殘響且音量穩定的 WAV。技能
wrapper 會以 FFmpeg 建立暫時的 24 kHz mono PCM16 版本，不修改原檔。

高相似度的 ICL voice clone 必須提供與參考音訊完全一致的逐字稿；標點、數字
讀法、漏字與多字都可能降低音色和韻律一致性。沒有逐字稿時仍可只使用
`--ref-wav` 的 speaker embedding 路徑，但通常不如 ICL 完整。

## 主要用法

直接傳入文字：

```powershell
qwen-voice-clone `
  -Text "這是一段使用參考聲音合成的繁體中文旁白。" `
  -ReferenceWav reference.wav `
  -ReferenceText "這是參考音訊實際說出的完整內容。" `
  -Language Chinese `
  -OutputPath output\clone.wav
```

從 UTF-8 文字檔產生旁白：

```powershell
qwen-voice-clone `
  -TextFile narration.txt `
  -ReferenceWav reference.wav `
  -ReferenceTextFile reference.txt `
  -Language Chinese `
  -Seed 42 `
  -OutputPath output\narration.wav
```

在專案目錄也可明確呼叫：

```powershell
pwsh -File scripts/qwen-voice-clone.ps1 `
  -TextFile narration.txt `
  -ReferenceWav reference.wav `
  -ReferenceTextFile reference.txt `
  -OutputPath output\narration.wav
```

輸出預設拒絕覆寫；只有使用者明確允許時才傳入 `-Force`。CUDA 不可用時可傳入
`-Cpu`，並在最終報告清楚標示實際使用的 backend。

## 旁白預設管線：合成、回聽、Agent 翻譯

正式影片旁白不要停在 `qwen-voice-clone`。使用整合 wrapper 產生語音並讓
whisper.cpp large-v3-turbo 做原語言回聽：

```powershell
pwsh -File scripts/qwen-narration-pipeline.ps1 `
  -TextFile narration.txt `
  -ReferenceWav reference.wav `
  -ReferenceTextFile reference.txt `
  -OutputPath output\narration.wav `
  -QwenLanguage Chinese `
  -WhisperLanguage zh `
  -ConfirmVoiceRights
```

腳本成功後建立 `narration.wav` 與 `narration.asr.srt`。目前 Agent 再直接把
cue 文字翻譯為 `narration.en.srt`，保留序號與時間碼，並執行
`validate_agent_translation.py`。不得使用 Whisper `--translate` 或 OpenAI API。
完整規則見 [narration.md](narration.md)。

## 裸 CLI

`qwen-tts` 從 stdin 讀取目標文字：

```powershell
Get-Content prompt.txt -Raw | qwen-tts `
  --model $env:QWENTTS_CPP_MODEL `
  --codec $env:QWENTTS_CPP_CODEC `
  --ref-wav reference.wav `
  --ref-text reference.txt `
  --lang Chinese `
  --seed 42 `
  -o output.wav
```

重複使用相同參考聲音時，可先建立 speaker embedding 與 RVQ codes，避免每次
重新編碼參考 WAV：

```powershell
qwen-codec `
  --model $env:QWENTTS_CPP_CODEC `
  --talker $env:QWENTTS_CPP_MODEL `
  -i reference.wav

Get-Content prompt.txt -Raw | qwen-tts `
  --model $env:QWENTTS_CPP_MODEL `
  --codec $env:QWENTTS_CPP_CODEC `
  --ref-spk reference.spk `
  --ref-rvq reference.rvq `
  --ref-text reference.txt `
  --lang Chinese `
  -o output.wav
```

## 驗證

```powershell
ffprobe -v error `
  -show_entries stream=codec_name,sample_rate,channels `
  -show_entries format=duration `
  -of json output.wav
```

完成條件：

- `qwen-tts` 結束碼為 0。
- WAV 存在、可解碼、24 kHz、mono、時長大於 0。
- 日誌確認實際 backend；不得只因建置含 CUDA 就宣稱 GPU 推論通過。
- 實際聆聽語音清晰度、音色相似度、語言與文字內容。
- 批次前先用短句與固定 seed 驗證，再處理完整旁白。

### 本機實測基線

已在 NVIDIA GeForce RTX 3070 Ti 上完成繁中 ICL voice clone：

- 參考音訊：繁中、精確逐字稿、經 wrapper 正規化為 24 kHz mono PCM16。
- 日誌：`Talker backend: CUDA0`、`ref_spk_emb=yes`、`icl=yes`。
- 輸出：6.48 秒、24 kHz、mono、PCM16 WAV。
- 模型內部總時間：1.768 秒，RTF 0.273。
- wrapper 端到端時間：約 4.02 秒。
- Whisper `large-v3-turbo` 反向轉錄能辨識完整句意；其中「語音」被辨識成同音
  近似字，因此 ASR 只證明內容可辨識，不等同於音色相似度或逐字完全正確。

正式使用仍需由人實際聆聽參考與輸出，驗收音色、情緒、韻律及是否有不自然
停頓；不得把短句 smoke 的效能或相似度直接外推到長篇旁白。

## 官方來源

- [qwentts.cpp](https://github.com/ServeurpersoCom/qwentts.cpp)
- [Qwen3-TTS GGUF](https://huggingface.co/Serveurperso/Qwen3-TTS-GGUF)
- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS)
