# Task 01 — Contracts

## Goal

驗證 Schema、config 與範例互相一致。

## Work

- 檢查 `typography/schemas/`。
- 增加 Python Schema smoke validator；可使用標準函式庫或 dev-only jsonschema。
- 驗證 `examples/demo.plan.json`。
- 驗證 template registry 不重複。
- 增加錯誤範例測試。

## Acceptance

- 未知 template、負時間、重複 ID 會失敗。
- 有效範例通過。
- 完成 T010、T090。
