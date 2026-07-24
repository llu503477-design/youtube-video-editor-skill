# Dynamic Typography Workflow

## Trigger

使用者要求：

- CapCut／Filmora 風格字幕
- 誇張字卡
- 逐字／逐詞高亮（P1 規劃中）
- 動態字幕
- 重點數字放大
- 問號、警告、CTA、章節標題
- 字幕美化、品牌字幕
- 避開人臉或畫面重要區域（P2 規劃中）

## Default Workflow

1. FFprobe 取得解析度、時長、fps 與音訊狀態。
2. 取得 SRT 或 word-level transcript。
3. 產生 Visual Plan。
4. 執行 validator。
5. 先產生 ASS 預覽。
6. 以 5～10 秒片段燒錄 smoke test。
7. 抽查一般字幕、強調字、強烈字卡。
8. 需要複雜動畫時才切換 Remotion。
9. 完整渲染。
10. FFprobe 與畫面抽查。
11. 保留 `.plan.json`、`.ass` 與 QA report。

## Renderer Selection

| Requirement | Renderer |
|---|---|
| 一般字幕 | ASS |
| 外框、陰影、底框 | ASS |
| 關鍵字變色 | ASS |
| 逐詞卡拉 OK | P1 規劃中，尚不可用 |
| 簡單放大、淡入 | ASS |
| 基本彈簧字卡 | Remotion demo renderer |
| 貼紙、粒子、多物件同步 | P1／P2 規劃中，尚不可用 |
| 可視化 Studio 預覽 | Remotion |
| renderer 失敗 fallback | ASS |

ASS + FFmpeg 是預設 renderer。Remotion demo renderer 已通過固定版本安裝、
兩項 timeline 測試、TypeScript typecheck、CLI render 與五張畫面抽查；它只承諾
目前的 CaptionPage 與基本 TitleCard，不代表 P1／P2 高級功能已完成。

## Agent Planning Contract

Agent 不直接產生任意 CSS 或 FFmpeg filter。先輸出：

```json
{
  "purpose": "punchline",
  "intensity": 0.9,
  "keywords": ["太誇張"],
  "templateId": "impact-slam",
  "strongEffect": true
}
```

Renderer 只接受模板 registry 中存在的 `templateId`。

## Reading Rules

- 一般字幕最多兩行。
- 不要讓所有字都跳。
- 每頁只突出 1～2 個重點。
- 字幕短於 650ms 或長於 3.2 秒時由 validator 提示可讀性警告，不阻斷合法 SRT。
- 文字密度過高時先重新分頁，不先縮成極小字。
- 強烈字卡不可連續出現。
- 文字不得壓住平台底部 UI 安全區。

## Output Naming

```text
<base>.typography.plan.json
<base>.typography.ass
<base>.typography.qa.json
<base>.typography.mp4
```
