# YouTube Video Typography Development Pack

這是 `stevenke1981/youtube-video-editor-skill` 內可獨立測試與執行的功能子專案，用來加入：

- CapCut／Filmora 風格的動態字卡
- 繁體中文字幕自動斷句與高亮
- 語意驅動的 punchline、warning、number、CTA、chapter 字卡
- ASS + FFmpeg 的可運作 MVP
- 可選的 Remotion demo renderer（已通過安裝、測試、typecheck 與 CLI render）
- 品牌樣式、效果預算、安全區與 QA Schema
- 給 GPT-5.3 Codex Spark 的細粒度實作任務與驗收規則

## 目錄定位

本開發包採「子專案整合」。實作、契約與測試保留在本目錄；主專案只提供
`scripts/typography.ps1`、依賴檢查、技能路由與整合測試。

```text
youtube-video-typography-devpack/
├─ scripts/                         # 可立即運作的 Python / PowerShell MVP
├─ tests/                           # MVP 單元測試
├─ typography/                      # Schema、設定、Prompt、Remotion 骨架
├─ workflows/                       # Codex 工作流程文件
├─ examples/                        # 範例 SRT、計畫與品牌設定
├─ integration/                     # 要附加到原專案文件的內容
├─ tasks/                           # Spark 分階段任務
├─ apply-overlay.ps1                # 舊 overlay 命令的遷移提示
├─ CODEX_SPARK_MASTER_PROMPT.md      # 可直接交給 Spark 的主提示詞
├─ SPEC.md / PLAN.md / TODOS.md
└─ TEST.md / FINAL.md
```

## 主專案整合方式

從主專案根目錄使用薄 wrapper；不要把本目錄的 implementation 再複製到 root：

```powershell
pwsh -File scripts/typography.ps1 plan `
  -InputPath youtube-video-typography-devpack/examples/demo.zh-TW.srt `
  -OutputPath output/demo.plan.json
```

`integration/` 保留原始整合建議作為設計參考，不是需要再次套用的安裝步驟。

## MVP 快速使用

### 1. 由 SRT 產生語意視覺計畫

```powershell
pwsh -File scripts/typography.ps1 plan `
  -InputPath examples/demo.zh-TW.srt `
  -OutputPath output/demo.plan.json
```

### 2. 產生動態 ASS

```powershell
pwsh -File scripts/typography.ps1 ass `
  -InputPath output/demo.plan.json `
  -OutputPath output/demo.ass
```

### 3. 驗證計畫

```powershell
pwsh -File scripts/typography.ps1 validate `
  -InputPath output/demo.plan.json `
  -OutputPath output/demo.qa.json
```

### 4. 燒錄到影片

```powershell
pwsh -File scripts/typography.ps1 render `
  -InputPath input.mp4 `
  -PlanPath output/demo.plan.json `
  -AssPath output/demo.ass `
  -OutputPath output/demo-captioned.mp4
```

所有命令預設拒絕覆寫。只有使用者明確允許時才加入 `-Force`。

## 直接使用 Python

```powershell
python scripts/typography_plan.py `
  examples/demo.zh-TW.srt `
  output/demo.plan.json

python scripts/generate_dynamic_ass.py `
  output/demo.plan.json `
  output/demo.ass

python scripts/validate_typography_project.py `
  output/demo.plan.json `
  --report output/demo.qa.json
```

## 測試

```powershell
python -m unittest tests.test_typography -v
```

需要 FFmpeg 的 smoke test：

```powershell
pwsh -File scripts/check-typography-dependencies.ps1
```

## Remotion 高級渲染

MVP 先使用 ASS + libass，確保在 Windows 與既有 FFmpeg 產線中快速落地。

Remotion demo renderer 已完成固定版本安裝、兩項 timeline 測試、typecheck、
CLI render 與五張畫面抽查。它仍不包含逐詞 karaoke、人臉避讓、貼紙／粒子與
自動修復。進入子專案：

```text
typography/remotion/
```

安裝：

```powershell
cd typography/remotion
npm ci
npm test
npm run typecheck
npm run render:demo
npm run studio
```

依序完成 `tasks/04-remotion-renderer.md` 到 `tasks/07-visual-qa.md`。

## 最重要的實作原則

1. 一般字幕以可閱讀為優先。
2. 強烈字卡必須有語意理由。
3. 每 10 秒的強效果數量受效果預算限制。
4. 文字、顏色、動畫只能由已驗證模板與品牌設定組成。
5. 任何輸出不得默認覆寫。
6. 複雜影片先以 5～10 秒短片段 smoke test。
7. 未通過程式 QA 與視覺抽查，不得宣稱完成。
