# GPT-5.3 Codex Spark 主提示詞

將以下內容貼給 GPT-5.3 Codex Spark，並把本開發包放在
`youtube-video-editor-skill` 專案根目錄。

---

你正在擴充 `youtube-video-editor-skill`，加入「動態字卡與智慧字幕」能力。

## 唯一事實來源

依序閱讀：

1. `AGENTS.typography.md`
2. `SPEC.md`
3. `PLAN.md`
4. `TODOS.md`
5. 當前階段對應的 `tasks/*.md`
6. 僅在需要時讀取 `workflows/dynamic-typography.md`

不要一次載入所有檔案，不要自行改變已定義的 JSON 契約。

## 工作模式

- 一次只完成一個 task 檔案。
- 每次修改保持小型、可測試、可回退。
- 先檢查現況，再修改。
- 不要只寫文件；每個功能 task 必須有程式碼、測試或可執行驗證。
- 不得以「理論上可行」取代實際執行測試。
- 不得刪除使用者檔案。
- 不得執行 `git push --force`。
- 不得覆寫既有輸出，除非使用者明確要求。
- 發現不影響安全的細節缺失時，採合理預設並記錄，不要停下詢問。
- 遇到破壞性操作、憑證、付費服務或需要權利確認的素材時才停止。

## 每輪固定流程

1. 從 `TODOS.md` 選取第一個未完成且無前置阻塞的項目。
2. 將其標記為 `IN_PROGRESS`。
3. 實作最小可驗收切片。
4. 執行該 task 指定測試。
5. 修正到測試通過。
6. 更新 `TODOS.md`、`TEST.md` 與必要文件。
7. 提交本輪證據摘要：
   - 修改檔案
   - 執行命令
   - 測試結果
   - 尚未完成項目
8. 再進入下一個項目，直到目前 task 全部完成。

## 架構邊界

- `scripts/*.py`：無額外 Python 套件的 deterministic MVP。
- `scripts/*.ps1`：Windows 安全 wrapper，不以字串拼接 shell 指令。
- `typography/schemas/*.json`：Agent 與 Renderer 的穩定契約。
- `typography/config/*.json`：品牌與設計規則。
- `typography/remotion/`：高級動畫，不能破壞 ASS MVP。
- `tests/test_typography.py`：MVP 回歸測試。
- Remotion 測試放在 `typography/remotion/src/**/*.test.ts`。

## 完成定義

只有以下全部成立才能更新 `FINAL.md` 為完成：

- Python 測試全部通過。
- PowerShell wrapper 在 Windows 可執行。
- FFmpeg 短片 smoke test 成功。
- 產生的 ASS 可被 libass 正常讀取。
- 正常字幕、警告、數字、笑點、章節、CTA 各有測試。
- 預設拒絕覆寫。
- 無字型載入錯誤。
- 至少抽查三個字幕時間點與兩個強字卡時間點。
- Remotion 階段完成時，Studio 預覽與 CLI render 都成功。
- `TODOS.md` 沒有未處理的 P0/P1。
- `FINAL.md` 記錄實際命令與結果，不能填寫假結果。

現在從 `tasks/00-baseline.md` 開始，不要跳階段。
