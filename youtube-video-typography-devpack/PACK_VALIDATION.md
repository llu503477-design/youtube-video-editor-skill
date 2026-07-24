# Pack Validation

驗證日期：2026-07-24

## 已實際執行

```text
python -m unittest tests.test_typography -v
```

結果：

```text
Ran 24 tests
OK
```

另已執行：

- Python `compileall`
- JSON 語法解析
- SRT -> Visual Plan
- Visual Plan -> ASS
- Visual Plan validator
- FFmpeg 7.1.3 + libass 實際燒錄
- FFprobe 輸出檢查
- `pwsh -File scripts/check-typography-dependencies.ps1`
- `scripts/check-dependencies.ps1`（含 typography 子檢查）

## FFmpeg Smoke Result

```text
Video: H.264, 1080x1920
Audio: AAC
Duration: 14.000000 seconds
Output size: 744532 bytes
```

## Remotion 檢核

- 固定版本 `npm install`：255 packages、0 vulnerabilities
- `npm test`：2 tests、OK
- `npm run typecheck`：OK
- `npm run render:demo`：既有輸出預設拒絕覆寫
- `npm run render:demo -- -Force`：390 frames、H.264、994.4 kB，舊檔已備份
- 五張 1080×1920 PNG 人工抽查：OK

## 尚未交付

- Remotion Studio 互動操作
- 逐詞 karaoke 與雙語 visual plan
- 人臉／產品避讓
- 視覺模型 QA 與自動修復

上述項目保留在 P1／P2，不影響已驗收的 ASS MVP 與 Remotion demo renderer。
