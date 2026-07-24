# 歷史整合參考（root README 已完成整合）

## 動態字卡與智慧字幕

```powershell
# SRT -> Visual Plan
pwsh -File scripts/typography.ps1 plan `
  -InputPath captions.zh-TW.srt `
  -OutputPath output/captions.plan.json

# Visual Plan -> ASS
pwsh -File scripts/typography.ps1 ass `
  -InputPath output/captions.plan.json `
  -OutputPath output/captions.ass

# 驗證
pwsh -File scripts/typography.ps1 validate `
  -InputPath output/captions.plan.json `
  -OutputPath output/captions.qa.json

# 燒錄
pwsh -File scripts/typography.ps1 render `
  -InputPath input.mp4 `
  -PlanPath output/captions.plan.json `
  -AssPath output/captions.ass `
  -OutputPath output/input-typography.mp4
```

支援一般字幕、警告、數字、問題、笑點、章節及 CTA。視覺計畫為可編輯 JSON，
同一份計畫可交給 ASS 或已驗收的 Remotion demo renderer。逐詞 karaoke、
人臉避讓、貼紙／粒子與自動修復仍屬 P1／P2。
