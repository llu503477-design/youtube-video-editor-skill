# SPEC — Dynamic Typography and Smart Captions

## 1. Goal

擴充既有影片 Skill，使 Agent 能產生類似 CapCut／Filmora 的：

- 高可讀字幕
- 逐詞高亮
- 語意關鍵字強調
- 誇張但有節制的字卡
- 品牌一致的文字視覺
- 可驗證、可重新編輯的 timeline JSON

## 2. Scope

### P0 — 必須完成

- SRT 解析
- 語意分類
- 視覺計畫 JSON
- ASS 產生器
- FFmpeg 燒錄 wrapper
- 不覆寫保護
- Schema／計畫驗證
- 效果預算
- 單元測試
- 範例檔

### P1 — 應完成

- 自訂 Brand Kit
- 雙語字幕資料模型
- word-level timestamp 輸入
- 卡拉 OK／逐詞高亮
- 多種模板
- FFprobe 驗證
- 短片 smoke test
- Remotion Studio 預覽
- Remotion CLI render

### P2 — 進階

- 人臉／產品避讓
- 畫面對比分析
- Lottie／WebM Alpha 貼紙
- 音效節點
- 視覺模型 QA
- 自動修正循環
- 可視化時間軸編輯器

## 3. Functional Requirements

### FR-001 Transcript Input

支援：

- UTF-8 SRT
- transcript JSON
- word-level timestamps
- zh-TW、英文及混合文字

### FR-002 Semantic Classification

每個字幕事件必須輸出：

- `purpose`
- `emotion`
- `intensity`
- `keywords`
- `templateId`
- `strongEffect`
- `readingPriority`

最少類型：

- `normal_dialogue`
- `important_fact`
- `number`
- `warning`
- `question`
- `answer`
- `punchline`
- `chapter_title`
- `quotation`
- `call_to_action`

### FR-003 Visual Plan

Visual Plan 必須符合 `typography/schemas/visual-plan.schema.json`。

所有時間使用秒，必須滿足：

```text
0 <= start < end <= project.duration
```

### FR-004 Caption Layout

直式 1080×1920 預設：

- 最多 2 行
- 建議每行 8～14 個中文字
- 最多 18 個中文字
- 畫面寬度不超過 84%
- 一般字幕位於 y=72% 附近
- 底部安全區至少 12%
- 正文字號 54～68
- 強調字號 70～92

### FR-005 Effect Budget

預設每 10 秒：

- 強烈字卡最多 1 個
- 中度強調最多 4 個
- 一般字幕不限，但只能使用輕微淡入或穩定高亮

超出時由規劃器降級，不得直接疊加全部效果。

### FR-006 ASS Renderer

必須產生：

- 有效 ASS header
- PlayResX／PlayResY
- 字幕樣式
- 事件時間碼
- 安全的文字 escaping
- UTF-8 output

### FR-007 FFmpeg Render

- 使用 `-n` 作為預設。
- 明確 `-Force` 才可用 `-y`。
- 以參數陣列執行。
- 失敗時不得保留被誤認為完成的正式輸出。
- 完成後執行 FFprobe。

### FR-008 Remotion Renderer

Remotion 層讀取相同 Visual Plan，不建立第二套不相容格式。

至少提供：

- CaptionPage
- KeywordHighlight
- ImpactCard
- WarningCard
- NumberCard
- ChapterCard
- CTA Card

### FR-009 QA

程式 QA：

- 時間軸
- 模板 ID
- 文字長度
- 最大行數
- 效果預算
- 解析度
- 色彩格式
- 輸出存在／大小／串流

視覺 QA：

- 溢位
- 安全區
- 對比
- 遮擋
- 字體
- 動畫密度

## 4. Non-functional Requirements

- Windows 10/11 與 PowerShell 7 優先。
- Python MVP 只使用標準函式庫。
- Node/Remotion 為選用依賴。
- 渲染結果 deterministic；隨機效果必須有 seed。
- JSON Schema 有版本號。
- 錯誤訊息可在 CP950 終端安全顯示。
- 可在沒有網路時執行已安裝依賴的渲染。
- 不內嵌字型二進位檔。

## 5. Out of Scope for Initial Release

- 完整 GUI 編輯器
- 雲端渲染
- 自動下載商用素材
- 自動發布到 YouTube
- 未授權的音效／字型／貼紙
- 使用私有 API 進行人臉辨識
