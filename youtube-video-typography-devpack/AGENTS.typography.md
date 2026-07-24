# AGENTS — Dynamic Typography Module

## Mission

在不破壞既有 `youtube-video-editor-skill` 的前提下，建立可重現、可測試、
可由 Agent 控制的動態字幕與字卡系統。

## Non-negotiable Rules

- 保留原始影片與字幕。
- 預設拒絕覆寫。
- 不以字串拼接外部命令；使用參數陣列。
- 輸入、輸出與暫存路徑都必須支援空白與非 ASCII 字元。
- 所有文字檔使用 UTF-8。
- 不提交字型檔、影片、模型、音訊或大型二進位資產。
- 只引用有授權的圖片、貼紙、音效與字型。
- 一般字幕不得過度動畫。
- 強烈效果必須符合語意分類及效果預算。
- 未驗證的視覺結果不得標示完成。

## Permission Policy

允許直接執行：

- 讀取專案檔案
- 建立新程式碼與測試
- 安裝專案內 npm 套件
- 執行 Python、PowerShell、Node、FFmpeg、FFprobe
- 建立暫存測試影片
- 修改本模組新增的檔案
- 更新規格、測試與 TODO 狀態

必須停止並取得使用者同意：

- 刪除非本次建立的檔案
- `rm`、`rmdir`、`del`、`Remove-Item -Recurse` 指向使用者資料
- 覆寫既有正式輸出
- `git push --force`
- 修改 Git 歷史
- 上傳素材或資料到外部服務
- 使用付費 API
- 下載或嵌入授權不明的字型、音效、貼紙

## Work Partition for Spark

每次 task 應控制在：

- 1 個主要功能
- 1～5 個生產檔案
- 1～3 個測試檔案
- 一組明確命令
- 可在單次上下文內驗收

不要同時重構 MVP 與 Remotion。先保證 deterministic MVP，再增加高級渲染。

## Required State Files

- `TODOS.md`：唯一進度來源。
- `TEST.md`：記錄測試命令與真實結果。
- `FINAL.md`：完成門檻與交付摘要。
- 不建立第二套互相衝突的進度檔。

## Failure Classes

### Class A — Input / Environment

例如 FFmpeg、Python、Node、字型缺失。提供明確診斷與安裝命令，不改動輸入。

### Class B — Contract

Schema、模板 ID、時間軸或顏色格式錯誤。拒絕渲染並輸出可定位錯誤。

### Class C — Render

FFmpeg、libass、Remotion render 失敗。保留日誌，不發布部分成品。

### Class D — Visual QA

遮住人臉、超出安全區、低對比、效果太密。回到 layout／style 修正，不改寫字幕語意。

## Completion Evidence

每一階段至少記錄：

- 修改檔案清單
- 實際命令
- return code
- 測試數量與結果
- 產物路徑
- 已知限制
