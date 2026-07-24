# CHANGE_LOG — YouTube Video Editor Skill

## 2026-07-24 — Auto-Editor 31 Redesign

### Added
- **scripts/install-auto-editor.ps1** — Pins and verifies official Auto-Editor 31.3.2 Windows binaries, installs them on the current user's PATH, and preserves replaced runtimes as backups
- **scripts/auto-edit.ps1 / auto-edit.cmd** — Preview-first wrapper with named pacing profiles, safe outputs, NLE export, custom expressions, and render validation
- **tests/test_skill_scripts.py** — Auto-Editor wrapper argument, preview, output, and overwrite regression tests

### Changed
- **auto-editing/** — Replaced obsolete pip, `min-silence`, and `jumpcutter` guidance with the current Auto-Editor 31 CLI and a single preview-to-render workflow
- **SKILL.md / README.md** — Added global installation, profile selection, prompt guidance, and timeline-ordering rules
- **workflows/** — Full and batch pipelines now require a representative preview before approved rendering and fail closed instead of silently using unedited input
- **scripts/check-dependencies.ps1 / validate.ps1** — Accept the version-only output used by current Auto-Editor releases

## 2026-06-30 — Initial Creation

### Added
- **SKILL.md** — Full skill entry point with philosophy, ecosystem matrix, architecture, quality gates, and violation rules
- **ffmpeg-core/basic-editing.md** — FFmpeg trim, cut, merge, crop, resize, speed, format conversion
- **ffmpeg-core/subtitles.md** — Burn SRT/ASS subtitles with force_style customization
- **ffmpeg-core/audio-bgm.md** — Add BGMs, mix audio tracks, replace audio, adjust volume
- **ffmpeg-core/filters-effects.md** — Apply video filters, transitions, watermark, text overlay
- **auto-editing/silence-removal.md** — Auto-editor and FFmpeg-based silence detection & removal
- **auto-editing/jump-cut.md** — Jump cut techniques and pipeline
- **ai-subtitles/whisper-pipeline.md** — Whisper/Whisper.cpp/faster-whisper subtitle generation
- **ai-subtitles/ffmpeg8-whisper.md** — FFmpeg 8.0 native whisper filter
- **youtube-download/yt-dlp.md** — yt-dlp commands for YouTube downloading
- **mcp-tools/mcp-video.md** — mcp-video MCP server installation and usage
- **scripts/validate.ps1** — Pipeline validation script
- **scripts/check-dependencies.ps1** — Dependency check script
- **workflows/full-pipeline.md** — End-to-end video production workflow
- **workflows/batch-processing.md** — Batch video processing workflow

## 2026-06-30 — Bilingual Subtitle Update (zh-TW + EN)

### Changed
- **SKILL.md** — Updated subtitle pipeline diagram to bilingual 2-pass flow, added bilingual quality gates
- **ffmpeg-core/subtitles.md** — Added "Bilingual Subtitles" section with Methods A (merged SRT), B (ASS dual-style), and C (YouTube dual-track), merge/generate Python scripts, bilingual Best Practices
- **ai-subtitles/whisper-pipeline.md** — Changed default language from `en` to `zh`, added bilingual pipeline example with Python code, updated full pipeline script with `-Bilingual` and `-AssFormat` switches
- **ai-subtitles/ffmpeg8-whisper.md** — Changed `language=en` to `language=zh` in all examples, added bilingual pipeline section with two-pass approach
- **workflows/full-pipeline.md** — Updated Stages 4/6 to support bilingual + ASS flow, added `-Bilingual`/`-AssFormat` parameters, updated usage examples, quality checklist, and troubleshooting
- **workflows/batch-processing.md** — Added `-Bilingual`/`-AssFormat`/`-SubtitleLang` parameters, bilingual subtitle generation and burning steps

### Added
- **scripts/merge_bilingual_srt.py** — Merge zh-TW + EN SRT into bilingual SRT (Chinese main + English secondary)
- **scripts/generate_bilingual_ass.py** — Generate bilingual ASS with zh-TW style (24px) and EN style (18px)

## 2026-06-30 — Video Narration / Voiceover (narrate.py + Edge-TTS)

### Added
- **ai-subtitles/narration.md** — Comprehensive narration guide covering TTS, language selection, stage-by-stage intro, audio ducking, three narration modes (intro/full/summary), and Edge-TTS voice reference table
- **scripts/narrate.py** — Full narration generation script: reads SRT subtitles, generates per-segment narration (template-based intro/read-aloud/summary), synthesizes via Edge-TTS, outputs WAV with timing markers; supports `--subs`, `--script`, `--lang`, `--voice`, `--mode`, `--offset`, `--pause`
- **SKILL.md** — Added Narration Generation stage to architecture diagram, quick reference with narration commands, quality gates for narration timing and ducking
- **ffmpeg-core/audio-bgm.md** — Added "Narration Auto-Ducking" and "Three-Layer Mix" sections with sidechaincompress examples; added narration mixing tips to Pro Tips
- **workflows/full-pipeline.md** — New `Stage 5/8: Narration Generation`, added `-Narrate`, `-NarrateLang`, `-NarrateVoice`, `-NarrateMode`, `-NarrateScript` parameters; Stage 6/8 audio mixing now supports narration ducking with sidechaincompress; updated stages diagram; usage examples
- **workflows/batch-processing.md** — Added narration parameters (`-Narrate`, `-NarrateLang`, `-NarrateVoice`, `-NarrateMode`); narration generation step; narration ducking in audio mixing

## 2026-06-30 — Subtitle Background Option (SubBg: none / black)

### Added
- **ffmpeg-core/subtitles.md** — New "Subtitle Background Options" section comparing `none` (BorderStyle=1, transparent + outline+shadow) vs `black` (BorderStyle=4, black box behind text only), with ASS style mapping
- **SKILL.md** — Added `-SubBg none/black` to pipeline architecture diagram and quality gates
- **workflows/full-pipeline.md** — Added `-SubBg` parameter (`ValidateSet: none, black`), dynamic background style in Stage 6 subtitle burning
- **workflows/batch-processing.md** — Added `-SubBg` parameter, dynamic background style in subtitle burning step
- **scripts/generate_bilingual_ass.py** — Added `--background` CLI argument (`black`/`none`), generates BorderStyle=4 (black box) or BorderStyle=1 (transparent) ASS headers

### Changed
- **ffmpeg-core/subtitles.md** — Updated `force_style` parameter table for BorderStyle documentation; split "半透明背景" into "無黑底" and "黑底背景" style templates; added background choice to Best Practices

## 2026-06-30 — v1.1: Large Font + Black Background + EN→zh-TW Pipeline

### Changed
- **SKILL.md** — Upgraded to v1.1, added MarianMT/OpenCC to ecosystem matrix, added full EN→zh-TW bilingual pipeline section, added `--drawbox` parameter documentation, updated subtitle font references from 24px→48px and 18px→36px
- **ffmpeg-core/subtitles.md** — Updated default font sizes to 48px(zh-TW)/36px(EN), added BorderStyle=4 opaque black background as default, added "Covering Hardcoded Subtitles" section with drawbox methods, updated Best Practices with new font sizes and drawbox guidance, updated ASS style reference table
- **scripts/generate_bilingual_ass.py** — FontSize zh-TW: 24→48, EN: 18→36, BorderStyle: 1→4, BackColour: semi-transparent→opaque black, added Bold=1 for zh-TW, added drawbox usage hint in output
- **scripts/generate_bilingual_from_en.py** — FontSize zh-TW: 24→48, EN: 18→36, BorderStyle: 1→4, BackColour: opaque black, added `--drawbox` and `--box-height` CLI arguments, added drawbox filter support in burn step

### Added
- **scripts/generate_bilingual_from_en.py** — Complete pipeline: faster-whisper EN transcribe → MarianMT EN→zh-CN → OpenCC zh-CN→zh-TW → bilingual ASS → FFmpeg burn with optional drawbox
- SKILL tags: `bilingual-subtitle`, `zh-TW`, `traditional-chinese`, `translation`, `marianmt`, `opencc`, `s2t`, `en-to-zh`

## 2026-06-30 — v1.2: Dynamic Font Scaling + Noto Sans TC Open-Source Font

### Problem
- Fixed font sizes (zh=48px, en=36px) were too large for 720p videos, occupying excessive screen area
- Microsoft JhengHei font has restrictive commercial-use licensing
- BorderStyle=4 (black box) as default was visually heavy for clean content

### Changed
- **All files** — Font family changed from `Microsoft JhengHei` → **`Noto Sans TC`** (Google/Adobe open-source, free for commercial use, SIL OFL license)
- **Default subtitle style** — Changed from BorderStyle=4 (black box) → **BorderStyle=1** (outline+shadow, no background fill). Keeps screen clean
- **Base font sizes** (at 1080p reference): zh-TW=**22px** (was 48px), EN=**16px** (was 36px)
- **Bottom margins** increased: zh-TW **MarginV=50**, EN **MarginV=30** to prevent clipping at screen bottom

### Added
- **Dynamic font scaling** — `ffprobe` auto-detects video height, computes scale factor relative to 1080p, proportionally adjusts font sizes, outline width, shadow distance, and margin. Clamped to 0.44–4.0× (480p–4320p range)
  - 720p → zh≈15px, en≈11px
  - 1080p → zh=22px, en=16px
  - 2160p (4K) → zh≈44px, en≈32px
- **scripts/generate_bilingual_ass.py** — New `--video-height` and `--scale` CLI arguments for automatic font scaling. Default changed to `--background none`
- **workflows/full-pipeline.md** — Inline font scaling block using ffprobe before subtitle filter selection
- **workflows/batch-processing.md** — Inline font scaling block for per-video resolution-adaptive subtitles
- **ai-subtitles/whisper-pipeline.md** — ASS generation now auto-detects video height with ffprobe

### Removed
- `scripts/generate_bilingual_from_en.py` (EN→zh-TW pipeline script) — no longer maintained (deprecated in v1.2)

### File Summary
| File | Changes |
|------|---------|
| ffmpeg-core/subtitles.md | New defaults (22/16, Noto Sans TC, BorderStyle=1, dynamic scaling), updated ASS example, style table, popular styles, SubBg section |
| scripts/generate_bilingual_ass.py | 22/16 defaults, Noto Sans TC, --background none default, +--scale/--video-height |
| SKILL.md | Updated quick reference command examples, added font scaling note |
| workflows/full-pipeline.md | Added ffprobe font scaling block, updated all subtitle filter strings |
| workflows/batch-processing.md | Added ffprobe font scaling block, updated subtitle filter strings |
| ai-subtitles/whisper-pipeline.md | Updated SRT/ASS filter strings with new defaults, added ffprobe call for ASS |
| ai-subtitles/ffmpeg8-whisper.md | Updated force_style example with Noto Sans TC and new sizes |
| auto-editing/silence-removal.md | Updated force_style example |
| CHANGE_LOG.md | This entry |

## 2026-06-30 — v1.3: Narration Subs Timing, Bilingual Spacing Fix, YouTube Thumbnail

### Problem
1. **Narration subtitles** — When `narrate.py` generates narration, the original SRT subtitles don't match the narration text (generated from templates). No way to display what the narrator is saying as on-screen text.
2. **Bilingual subtitle overlap** — zh-TW and EN lines used different MarginV (50 vs 30), causing misalignment on some renderers.
3. **Missing thumbnail generation** — No integrated YouTube thumbnail creation with eye-catching text.

### Changed
- **scripts/narrate.py** — Added `--output-subs <path.srt>`: generates SRT with timing matching the actual TTS audio. Each subtitle entry appears when the narrator speaks that segment, computed from the concatenated WAV timeline. Also added `--output-subs-lang`.
- **scripts/generate_bilingual_ass.py** — Fixed zh-TW/EN margin: both styles now use the same MarginV (50 at 1080p, scaled). Lines stack naturally without overlap or excessive gap.

### Added
- **scripts/thumbnail.py** — YouTube thumbnail generator (Pillow, 1280×720). Background from image/video frame, large bold title with multi-layer glow, subtitle text, gradient overlay, auto CJK font. Parameters: `--bg|--video`, `--title`, `--subtitle`, `--title-size`, `--sub-size`, `--text-color`, `--glow`.
- **ffmpeg-core/thumbnail.md** — Thumbnail docs with CLI reference, design tips, pipeline integration.
- **ai-subtitles/narration.md** — New section "同步輸出旁白字幕 (--output-subs)".
- **SKILL.md** — Thumbnail in architecture diagram + quick reference; `--output-subs` example in narration section.

### File Summary
| File | Changes |
|------|---------|
| scripts/narrate.py | +`--output-subs`, +`--output-subs-lang`; +`generate_narration_srt()`, `ms_to_srt_time()`, `write_srt()` |
| scripts/generate_bilingual_ass.py | EN_MARGINV 30→50 (same as ZH_MARGINV, 1080p base) |
| scripts/thumbnail.py | **New** — YouTube thumbnail generator |
| ffmpeg-core/thumbnail.md | **New** — Thumbnail docs |
| ai-subtitles/narration.md | +`--output-subs` section |
| SKILL.md | +thumbnail in diagram + quick reference; +`--output-subs` example |
| CHANGE_LOG.md | This entry |

## 2026-06-30 — v1.4: Built-in CapCut-like CLI (Self-Designed, FFmpeg Backend)

### Changed
- **SKILL.md** — Replaced anti-scope "應使用 GUI 工具如 CapCut" with built-in `capcut.ps1` CLI listing. Added CapCut CLI block to architecture diagram. Added full quick-reference examples.
- **Removed all references** to external `https://github.com/renezander030/capcut-cli.git` — the project now has its own CapCut-like CLI.

### Added
- **scripts/capcut.ps1** — Self-designed CapCut-like CLI with 8 commands, all backed by FFmpeg:
  - `trim` — clip segments via ffmpeg -ss/-to
  - `split` — split video at timestamp
  - `merge` — concat multiple files (concat demuxer + fallback)
  - `text` — drawtext overlay (white + black outline + shadow)
  - `audio` — mix BGM with original audio
  - `speed` — setpts + atempo filter
  - `subtitle` — burn SRT with styled force_style
  - `export` — re-encode for compatibility
  - `info` — ffprobe JSON summary
- **workflows/capcut-cli.md** — Comprehensive documentation with usage examples, parameter tables, pipeline integration guide, and FFmpeg mapping table.

### File Summary
| File | Changes |
|------|---------|
| SKILL.md | Removed CapCut anti-scope; added capcut.ps1 to scope + diagram + quick reference |
| scripts/capcut.ps1 | **New** — 8 commands, FFmpeg backend |
| workflows/capcut-cli.md | **New** — Full CLI documentation |
| CHANGE_LOG.md | This entry |
