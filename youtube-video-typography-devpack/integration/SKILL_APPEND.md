# 歷史整合參考（root SKILL 已完成整合）

在「資源導覽」加入：

```markdown
- 動態字卡、語意字幕、CapCut／Filmora 風格文字動畫：
  先讀取 [workflows/dynamic-typography.md](workflows/dynamic-typography.md)。
  優先使用 ASS + FFmpeg MVP；基本 CaptionPage／TitleCard 可使用
  `typography/remotion/`。逐詞 karaoke、貼紙與粒子仍未交付。
```

在執行規則加入：

```markdown
動態字幕與字卡必須先產生 `Visual Plan JSON`，再交給 ASS 或 Remotion renderer。
一般字幕以閱讀為優先；強烈效果必須符合語意分類與效果預算。所有輸出預設拒絕
覆寫，複雜效果先以 5～10 秒短片段驗證，完成後抽查一般字幕、強調字與字卡畫面。
```

在常用命令加入：

```powershell
pwsh -File scripts/typography.ps1 plan `
  -InputPath captions.zh-TW.srt `
  -OutputPath output/captions.plan.json

pwsh -File scripts/typography.ps1 render `
  -InputPath input.mp4 `
  -PlanPath output/captions.plan.json `
  -AssPath output/captions.ass `
  -OutputPath output/input-typography.mp4
```
