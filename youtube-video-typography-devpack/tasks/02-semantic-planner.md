# Task 02 — Semantic Planner

## Goal

完成穩定 SRT -> Visual Plan 管線。

## Work

- 擴充中文數字辨識。
- 支援 transcript JSON。
- 支援前後文但保持 deterministic。
- effect budget 保留最高強度事件。
- CLI 錯誤訊息可在 CP950 安全顯示。

## Acceptance

- warning、number、question、punchline、chapter、CTA 各有測試。
- 同一 10 秒超量效果會降級。
- 不覆寫。
- 完成 T020～T040。
