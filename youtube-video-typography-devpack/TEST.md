# TEST LOG

此檔只記錄實際執行結果。不要預先填寫 PASS。

## Required Commands

以下命令都從主 repo 根目錄執行：

```powershell
python -m unittest tests.test_typography -v
python tests/test_skill_scripts.py -v
```

```powershell
pwsh -File scripts/check-dependencies.ps1
```

```powershell
Push-Location youtube-video-typography-devpack/typography/remotion
npm ci
npm test
npm run typecheck
npm run render:demo
Pop-Location
```

## Test Matrix

| ID | Area | Expected |
|---|---|---|
| UT-001 | SRT parse | 毫秒與多行文字正確 |
| UT-002 | invalid SRT | fail closed |
| UT-003 | semantic warning | 選到 warning-alert |
| UT-004 | semantic number | 選到 big-number |
| UT-005 | semantic punchline | 選到 impact-slam |
| UT-006 | budget | 同一 10 秒過多強效果會降級 |
| UT-007 | ASS escape | `{}` 與換行安全 |
| UT-008 | ASS header | PlayRes 與 styles 存在 |
| UT-009 | overwrite | 未 force 拒絕覆寫 |
| UT-010 | validator | 負時間／未知模板失敗 |
| ST-001 | FFmpeg | 5 秒短片成功輸出 |
| ST-002 | FFprobe | 視訊與音訊串流有效 |
| VT-001 | Visual | 底部字幕可讀 |
| VT-002 | Visual | 中央字卡不溢位 |
| VT-003 | Visual | 強效果密度合理 |

## Execution Records

2026-07-24（Windows、PowerShell、Python 3.14.5、Node 24.15.0、npm 11.12.1）：

- `python -m unittest tests.test_typography -v` → OK（24 tests）
- 其中 `test_full_mvp_path_smoke` 於臨時目錄建立測試影片，實際執行
  plan → ass → validate → 使用既有 `-AssPath` render → FFprobe → `-Force`
  備份 → 自動 ASS 命名驗證。
- `npm install --ignore-scripts` → OK（255 packages、0 vulnerabilities）
- `npm test` → OK（2 tests）
- `npm run typecheck` → OK
- `npm run render:demo` 對既有輸出 → 預期拒絕覆寫
- `npm run render:demo -- -Force` → OK（390 frames、H.264、994.4 kB），
  舊檔保留為時間戳 backup
- 從 Remotion demo 的 1.0、2.2、3.0、4.2、6.2 秒抽取五張 1080×1920
  PNG；人工確認一般字幕、彈簧字卡、數字字卡、安全區及長字卡縮放皆未截斷。
