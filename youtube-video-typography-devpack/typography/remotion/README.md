# Remotion Demo Renderer

此資料夾是高級動畫階段，不取代 ASS MVP。

## Install

```powershell
npm install
```

相依版本已固定並由 `package-lock.json` 鎖定；CI／新環境優先使用 `npm ci`。

## Commands

```powershell
npm run studio
npm run typecheck
npm test
npm run render:demo
```

`src/demo-plan.json` 應由 `examples/demo.plan.json` 同步或透過 script 複製。

`render:demo` 預設拒絕覆寫 `out/demo-remotion.mp4`。只有使用者明確允許時使用
`npm run render:demo -- -Force`；wrapper 會先在同一檔案系統 staging，發布前再
備份既有輸出。
