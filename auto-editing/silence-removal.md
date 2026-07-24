# Auto-Editor 31 — Safe Silence Removal

## Design goals

Use the official Auto-Editor binary for analysis and rendering, but route normal skill usage
through `scripts/auto-edit.ps1`. The wrapper provides:

- preview-first operation;
- named pacing profiles instead of fragile ad-hoc flags;
- explicit output paths and overwrite protection;
- recoverable timestamped backups when `-Force` is intentional;
- output existence and non-empty validation;
- NLE export without rendering intermediate media.

Do not use the obsolete pip package or the old `min-silence` and `when:inactive` examples.
Auto-Editor 30+ changed its CLI surface; verify commands against `auto-editor --help`.

## Install globally on Windows

```powershell
pwsh -File scripts/install-auto-editor.ps1
auto-editor --version
auto-edit -?
```

The installer pins the official `31.3.2` Windows binary, verifies the GitHub release
SHA-256, installs it under `%LOCALAPPDATA%\auto-editor\bin`, adds that directory to the
current user's PATH, sets `AUTO_EDITOR_EXE`, and installs the `auto-edit` wrapper.

The upstream project recommends official release binaries and no longer publishes the CLI
on pip. On macOS use Homebrew; on Linux use the official release binary.

## Preview first

The wrapper defaults to `Preview`, so the first command analyzes cuts without rendering:

```powershell
auto-edit -InputPath input.mp4
auto-edit -InputPath input.mp4 -Profile Conservative -Mode Preview
```

Read the reported input/output duration and number of cuts. If the reduction is unexpectedly
large, lower the threshold by selecting a more conservative profile or passing a custom edit
expression.

## Profiles

| Profile | Edit expression | Margin | Smoothing | Intended use |
|---|---|---|---|---|
| `Conservative` | `audio:-34dB` | `0.35s,0.50s` | `0.40s,0.15s` | Interviews, tutorials, hesitant speech |
| `Balanced` | `audio:-28dB` | `0.25s,0.35s` | `0.25s,0.10s` | Default talking-head footage |
| `Aggressive` | `audio:-20dB` | `0.12s,0.18s` | `0.15s,0.08s` | Shorts and fast-paced delivery |
| `Podcast` | `audio:-32dB` | `0.40s,0.60s` | `0.50s,0.20s` | Natural conversational pacing |
| `Motion` | `motion:threshold=2%` | `0.20s,0.30s` | `0.25s,0.10s` | Silent screen or camera footage |
| `FastReview` | `audio:-28dB` | `0.20s,0.25s` | `0.25s,0.10s` | Keep silence at 8× instead of cutting |

The values are starting points, not universal truth. Background noise, microphone gain,
speaking style, music, and room tone materially affect audio analysis.

## Render

After approving the preview:

```powershell
auto-edit -InputPath input.mp4 `
  -OutputPath output/input-edited.mp4 `
  -Profile Balanced `
  -Mode Render
```

Optional controlled overrides:

```powershell
auto-edit -InputPath input.mp4 `
  -OutputPath output/input-edited.mp4 `
  -Mode Render `
  -EditExpression "audio:-26dB" `
  -Margin "0.30sec,0.45sec" `
  -Smooth "0.25sec,0.10sec" `
  -Transition "dissolve:0.12sec:1sec" `
  -AudioNormalize ebu `
  -Crf 21
```

Do not pass `-Force` casually. When used, the wrapper moves the old output to a timestamped
backup before rendering.

## Export to an NLE

```powershell
auto-edit -InputPath input.mp4 `
  -OutputPath output/input.otio `
  -Mode Export `
  -ExportFormat premiere-otio `
  -Profile Balanced
```

Supported wrapper exports are `premiere`, `premiere-otio`, `resolve`, `final-cut-pro`,
`shotcut`, `kdenlive`, and `v3`. Import the result and inspect every cut before destructive
timeline cleanup.

## Direct official CLI

Use direct CLI only when the wrapper does not expose a required upstream feature:

```powershell
# Preview
auto-editor input.mp4 --edit audio:-28dB --margin 0.25sec,0.35sec `
  --smooth 0.25sec,0.10sec --preview

# Render
auto-editor input.mp4 --edit audio:-28dB --margin 0.25sec,0.35sec `
  --smooth 0.25sec,0.10sec -o output.mp4

# Keep quiet sections at 8x
auto-editor input.mp4 --edit audio:-28dB -w:0 speed:8 -o review.mp4
```

Pass arguments as an array from automation code. Do not concatenate untrusted paths into a
shell string.

## Pipeline ordering

Run automatic editing before generating external subtitles, chapter timestamps, overlays,
or time-coded annotations. Removing time changes the entire downstream timeline.

Recommended order:

1. inspect source with FFprobe;
2. preview Auto-Editor;
3. render or export and manually review cuts;
4. transcribe the edited media with whisper.cpp;
5. create subtitles, narration, BGM, and final encode;
6. validate the final output.

## Verification

```powershell
ffprobe -v error -show_entries format=duration,size `
  -of default=noprint_wrappers=1 input.mp4
ffprobe -v error -show_entries format=duration,size `
  -of default=noprint_wrappers=1 output/input-edited.mp4
```

Listen around at least five cut boundaries. Verify that words, breaths needed for natural
phrasing, intentional pauses, music tails, and visual demonstrations were not truncated.
