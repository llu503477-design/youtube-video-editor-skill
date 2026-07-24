# PLAN — Implementation Architecture

## Architecture

```text
SRT / Transcript JSON
        │
        ▼
Transcript Parser
        │
        ▼
Semantic Planner
        │
        ▼
Effect Budget + Template Resolver
        │
        ▼
Visual Plan JSON
      ┌─┴──────────────────────┐
      ▼                        ▼
ASS Renderer              Remotion Renderer
      │                        │
      ▼                        ▼
FFmpeg/libass             Chromium Frames
      └──────────┬─────────────┘
                 ▼
             Final MP4
                 │
                 ▼
          Programmatic QA
                 │
                 ▼
            Visual Sampling
```

## Design Decision

### Why two renderers?

ASS + FFmpeg：

- 與既有 repo 相容
- 快速
- Windows 依賴少
- 適合字幕、逐詞高亮與基本字卡
- 作為可靠 fallback

Remotion：

- 適合複雜進出場
- 支援 React 元件化模板
- 可做貼紙、粒子、彈簧、遮罩、動態排版
- 適合 CapCut／Filmora 級視覺

兩者共用同一份 Visual Plan。

## Phases

### Phase 0 — Baseline

- 驗證現有測試
- 記錄 Python、PowerShell、FFmpeg、Node
- 不修改既有功能

### Phase 1 — Contracts

- Schema
- config
- example
- deterministic validation

### Phase 2 — Semantic Planner

- SRT parser
- classification
- keyword extraction
- effect budget
- JSON output

### Phase 3 — ASS MVP

- styles
- escapes
- event generation
- karaoke support
- FFmpeg wrapper
- unit tests

### Phase 4 — Remotion

- Studio
- composition
- template registry
- props validation
- CLI render
- snapshot tests

### Phase 5 — Layout Intelligence

- safe zones
- max-width fitting
- line breaking
- blocked zones
- fallback placement

### Phase 6 — Visual QA

- sample frame extraction
- overflow checks
- contrast score
- optional vision reviewer
- automatic retry policy

### Phase 7 — Integration

- update main SKILL routing
- README commands
- dependency checker
- full pipeline
- regression test

## Module Boundaries

```text
scripts/typography_core.py
  Pure parsing, planning, time and style utilities.

scripts/typography_plan.py
  CLI only. No rendering.

scripts/generate_dynamic_ass.py
  Visual Plan -> ASS.

scripts/validate_typography_project.py
  Contract and quality validation.

scripts/render-typography.ps1
  External process boundary.

typography/remotion/
  Advanced renderer. Reads the same plan.
```

## Rollback

- 所有新增檔案都具有獨立名稱。
- 不直接替換原有字幕產線。
- 主 `SKILL.md` 只增加路由說明。
- 發生問題時可移除 `typography/` 及 typography 專用檔案，不影響原功能。
