# check-dependencies.ps1 整合建議

在 `$dependencies` 中加入選用工具：

```powershell
@{ Name = "Node.js 20+"; Exe = "node"; Arguments = @("--version"); Pattern = "^v(?:2\d|[3-9]\d)\."; Optional = $true },
@{ Name = "npm"; Exe = "npm"; Arguments = @("--version"); Pattern = "^\d+\."; Optional = $true }
```

另外不要只依賴 `ffmpeg -version`，動態字幕工作開始前執行：

```powershell
ffmpeg -hide_banner -filters | Select-String -Pattern "\bass\b|\bsubtitles\b"
```

至少需要 `ass` 或 `subtitles` filter，並應確認 FFmpeg build 含 libass。
本開發包也提供獨立的：

```powershell
pwsh -File scripts/check-typography-dependencies.ps1
```
