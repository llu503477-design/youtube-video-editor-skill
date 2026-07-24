# Auto-Editor 31 — Jump-Cut Workflow

## Default workflow

Use one reproducible preview-to-render loop:

```powershell
# 1. Analyze without creating media
auto-edit -InputPath input.mp4 -Profile Balanced -Mode Preview

# 2. Render only after reviewing the statistics
auto-edit -InputPath input.mp4 `
  -OutputPath output/input-jumpcut.mp4 `
  -Profile Balanced `
  -Mode Render

# 3. Validate duration and inspect cut boundaries
pwsh -File scripts/validate.ps1 `
  -VideoPath input.mp4 `
  -OutputPath output/input-jumpcut.mp4
```

The previous `jumpcutter` path is no longer the default. Keeping one official analysis
engine reduces dependency drift and avoids maintaining two incompatible threshold models.

## Choose a strategy

### Talking-head and tutorial footage

Start with `Balanced`. Use `Conservative` when word endings or intentional pauses are cut.
Use `Aggressive` only for fast-paced content after a preview.

```powershell
auto-edit -InputPath lesson.mp4 -Profile Conservative -Mode Preview
```

### Podcast and interviews

Preserve more breathing room:

```powershell
auto-edit -InputPath interview.mp4 `
  -Profile Podcast `
  -Mode Preview
```

### Screen recordings or silent footage

Analyze motion instead of audio:

```powershell
auto-edit -InputPath demo.mp4 -Profile Motion -Mode Preview
```

For a specific region, use an official expression:

```powershell
auto-edit -InputPath demo.mp4 `
  -EditExpression "motion:threshold=2%,x=0.2,y=0.1,w=0.6,h=0.8" `
  -Mode Preview
```

### Review long footage without deleting silence

Fast-forward inactive sections:

```powershell
auto-edit -InputPath recording.mp4 `
  -OutputPath output/recording-review.mp4 `
  -Profile FastReview `
  -Mode Render
```

## Combine analysis methods

Auto-Editor expressions support boolean composition. Use them only after validating each
method independently:

```powershell
auto-edit -InputPath input.mp4 `
  -EditExpression "(or audio:-28dB motion:threshold=2%)" `
  -Mode Preview
```

For subtitle-aware editing, first create or embed subtitles that correspond to the source
timeline, then use the official `subtitle`, `word`, or `regex` method. Prefer generating final
delivery subtitles after jump cuts so downstream timing remains simple.

## Smooth hard cuts

Keep hard jump cuts by default. Add a short dissolve only if visual discontinuity is
distracting:

```powershell
auto-edit -InputPath input.mp4 `
  -OutputPath output/input-soft-cuts.mp4 `
  -Mode Render `
  -Profile Balanced `
  -Transition "dissolve:0.12sec:1sec"
```

The last value skips dissolves for source gaps shorter than one second, avoiding excessive
micro-transitions.

## Manual ranges

When a known section must always be removed or retained, call the official CLI directly:

```powershell
# Always remove the first 15 seconds
auto-editor input.mp4 --edit audio:-28dB --cut-out start,15sec -o output.mp4

# Always preserve an important demonstration
auto-editor input.mp4 --edit audio:-28dB --add-in 120sec,150sec -o output.mp4
```

Record manual ranges in the task log so the result is reproducible.

## Acceptance checklist

- Preview statistics were reviewed before rendering.
- Output uses a new path and the source remains unchanged.
- Output duration is plausible for the requested pacing.
- At least five cut boundaries were reviewed with audio.
- No word onset or ending is clipped.
- Intentional pauses and demonstrations remain understandable.
- External subtitles and chapters match the edited timeline.
- FFprobe can decode the result and reports expected streams.
