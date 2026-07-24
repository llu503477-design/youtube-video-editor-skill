#!/usr/bin/env python3
"""Deterministic helpers for video typography planning and ASS generation."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Iterable, Sequence

TIME_RE = re.compile(
    r"^(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{1,3})$"
)
RANGE_RE = re.compile(r"^\s*(.*?)\s*-->\s*(.*?)\s*$")

CONFIG_ROOT = Path(__file__).resolve().parents[1] / "typography" / "config"


def _load_config(name: str) -> dict:
    with (CONFIG_ROOT / name).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Typography config must be an object: {name}")
    return payload


TEMPLATE_REGISTRY = _load_config("template-registry.json")
EFFECT_BUDGET = _load_config("effect-budget.json")
CAPTION_RULES = _load_config("caption-rules.zh-TW.json")
TEMPLATE_IDS = {
    template["id"]
    for template in TEMPLATE_REGISTRY.get("templates", [])
    if isinstance(template, dict) and isinstance(template.get("id"), str)
}

WARNING_WORDS = ("千萬", "不要", "危險", "警告", "錯誤", "禁止", "小心")
PUNCHLINE_WORDS = ("太誇張", "誇張", "離譜", "太扯", "笑死", "竟然", "不可思議")
CTA_WORDS = ("訂閱", "按讚", "點讚", "分享", "留言", "下載", "追蹤", "購買")
CHAPTER_WORDS = ("第一", "第二", "第三", "首先", "接下來", "下一步", "步驟")
QUOTE_MARKS = ("「", "」", "『", "』", '"')
NUMBER_RE = re.compile(r"(?:\d+(?:[.,]\d+)?%?|\d+\s*(?:秒|分鐘|小時|天|元|塊))")


@dataclass(frozen=True)
class Cue:
    index: int
    start: float
    end: float
    text: str


def timestamp_to_seconds(value: str) -> float:
    match = TIME_RE.match(value.strip())
    if not match:
        raise ValueError(f"Invalid SRT timestamp: {value!r}")
    parts = {key: int(number) for key, number in match.groupdict().items()}
    if parts["m"] >= 60 or parts["s"] >= 60:
        raise ValueError(f"Out-of-range SRT timestamp: {value!r}")
    milliseconds = int(str(parts["ms"]).ljust(3, "0")[:3])
    return parts["h"] * 3600 + parts["m"] * 60 + parts["s"] + milliseconds / 1000


def seconds_to_ass(value: float) -> str:
    if value < 0:
        raise ValueError("ASS time cannot be negative")
    centiseconds = int(round(value * 100))
    hours, remaining = divmod(centiseconds, 360000)
    minutes, remaining = divmod(remaining, 6000)
    seconds, cs = divmod(remaining, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{cs:02d}"


def parse_srt_text(content: str) -> list[Cue]:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    blocks = re.split(r"\n{2,}", normalized)
    cues: list[Cue] = []

    for ordinal, block in enumerate(blocks, start=1):
        lines = [line.rstrip() for line in block.split("\n")]
        if len(lines) < 2:
            raise ValueError(f"Invalid SRT block {ordinal}: not enough lines")

        if lines[0].strip().isdigit():
            index = int(lines[0].strip())
            time_line_index = 1
        else:
            index = ordinal
            time_line_index = 0

        if time_line_index >= len(lines):
            raise ValueError(f"Invalid SRT block {ordinal}: missing time range")

        range_match = RANGE_RE.match(lines[time_line_index])
        if not range_match:
            raise ValueError(f"Invalid SRT block {ordinal}: bad time range")

        start = timestamp_to_seconds(range_match.group(1))
        end = timestamp_to_seconds(range_match.group(2))
        if end <= start:
            raise ValueError(f"Invalid SRT block {ordinal}: end must be after start")

        text_lines = lines[time_line_index + 1 :]
        text = "\n".join(text_lines).strip()
        if not text:
            raise ValueError(f"Invalid SRT block {ordinal}: empty text")

        cues.append(Cue(index=index, start=start, end=end, text=text))

    for previous, current in zip(cues, cues[1:]):
        if current.start < previous.start:
            raise ValueError("SRT cues must be sorted by start time")

    return cues


def parse_srt_file(path: str | Path) -> list[Cue]:
    return parse_srt_text(Path(path).read_text(encoding="utf-8-sig"))


def first_match(text: str, choices: Sequence[str]) -> str | None:
    return next((choice for choice in choices if choice in text), None)


def classify_text(text: str) -> dict:
    compact = re.sub(r"\s+", "", text)
    warning = first_match(compact, WARNING_WORDS)
    cta = first_match(compact, CTA_WORDS)
    punchline = first_match(compact, PUNCHLINE_WORDS)
    chapter = first_match(compact, CHAPTER_WORDS)
    number = NUMBER_RE.search(compact)

    if warning:
        return {
            "purpose": "warning",
            "emotion": "urgent",
            "intensity": 0.9,
            "keywords": [warning],
            "templateId": "warning-alert",
            "strongEffect": True,
            "readingPriority": "high",
        }
    if cta:
        return {
            "purpose": "call_to_action",
            "emotion": "encouraging",
            "intensity": 0.85,
            "keywords": [cta],
            "templateId": "cta-card",
            "strongEffect": True,
            "readingPriority": "high",
        }
    if punchline:
        return {
            "purpose": "punchline",
            "emotion": "surprised",
            "intensity": 0.9,
            "keywords": [punchline],
            "templateId": "impact-slam",
            "strongEffect": True,
            "readingPriority": "high",
        }
    if number:
        return {
            "purpose": "number",
            "emotion": "informative",
            "intensity": 0.72,
            "keywords": [number.group(0)],
            "templateId": "big-number",
            "strongEffect": False,
            "readingPriority": "high",
        }
    if chapter:
        return {
            "purpose": "chapter_title",
            "emotion": "neutral",
            "intensity": 0.62,
            "keywords": [chapter],
            "templateId": "chapter-title",
            "strongEffect": False,
            "readingPriority": "high",
        }
    if compact.endswith(("?", "？")):
        return {
            "purpose": "question",
            "emotion": "curious",
            "intensity": 0.6,
            "keywords": [],
            "templateId": "question-pop",
            "strongEffect": False,
            "readingPriority": "normal",
        }
    if any(mark in compact for mark in QUOTE_MARKS):
        return {
            "purpose": "quotation",
            "emotion": "reflective",
            "intensity": 0.55,
            "keywords": [],
            "templateId": "quote-card",
            "strongEffect": False,
            "readingPriority": "normal",
        }
    return {
        "purpose": "normal_dialogue",
        "emotion": "neutral",
        "intensity": 0.3,
        "keywords": [],
        "templateId": "clean-bottom",
        "strongEffect": False,
        "readingPriority": "normal",
    }


def is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def effect_budget_violations(
    events: Sequence[dict],
    *,
    window_seconds: float,
    max_strong: int,
) -> list[list[dict]]:
    """Return strong-effect groups that exceed a sliding-window budget."""
    if window_seconds <= 0 or max_strong < 0:
        raise ValueError("Invalid effect budget")
    strong_events = sorted(
        (
            event
            for event in events
            if isinstance(event, dict)
            and event.get("strongEffect") is True
            and is_finite_number(event.get("start"))
        ),
        key=lambda item: float(item["start"]),
    )
    violations: list[list[dict]] = []
    left = 0
    for right, event in enumerate(strong_events):
        event_start = float(event["start"])
        while (
            left <= right
            and event_start - float(strong_events[left]["start"]) >= window_seconds
        ):
            left += 1
        window = strong_events[left : right + 1]
        if len(window) > max_strong:
            violations.append(window)
    return violations


def apply_effect_budget(
    events: list[dict],
    window_seconds: float | None = None,
    max_strong: int | None = None,
) -> None:
    """Downgrade strong effects so every sliding window stays within budget."""
    if window_seconds is None:
        window_seconds = float(EFFECT_BUDGET["windowSeconds"])
    if max_strong is None:
        max_strong = int(EFFECT_BUDGET["strongEffects"])
    if window_seconds <= 0 or max_strong < 0:
        raise ValueError("Invalid effect budget")

    strong_events = [event for event in events if event.get("strongEffect")]
    strong_events.sort(
        key=lambda item: (-float(item["intensity"]), float(item["start"]))
    )
    kept: list[dict] = []
    for event in strong_events:
        event_start = float(event["start"])
        nearby_kept = sum(
            abs(event_start - float(existing["start"])) < window_seconds
            for existing in kept
        )
        if nearby_kept < max_strong:
            kept.append(event)
            continue
        event["strongEffect"] = False
        event["templateId"] = "clean-bottom"
        event["purpose"] = "important_fact"
        event["intensity"] = min(float(event["intensity"]), 0.65)


def build_visual_plan(
    cues: Iterable[Cue],
    *,
    width: int = 1080,
    height: int = 1920,
    fps: float = 30.0,
    language: str = "zh-TW",
    brand_id: str = "default-zh-tw",
) -> dict:
    cue_list = list(cues)
    if not cue_list:
        raise ValueError("At least one cue is required")
    if width <= 0 or height <= 0 or fps <= 0:
        raise ValueError("Invalid project dimensions or FPS")

    events: list[dict] = []
    for ordinal, cue in enumerate(cue_list, start=1):
        event = {
            "id": f"caption-{ordinal:04d}",
            "start": round(cue.start, 3),
            "end": round(cue.end, 3),
            "text": cue.text,
        }
        event.update(classify_text(cue.text))
        events.append(event)

    apply_effect_budget(events)
    duration = max(event["end"] for event in events)

    return {
        "schemaVersion": "1.0",
        "project": {
            "width": int(width),
            "height": int(height),
            "fps": float(fps),
            "duration": round(float(duration), 3),
            "language": language,
        },
        "brandId": brand_id,
        "events": events,
    }


def load_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_text_safely(
    path: str | Path,
    content: str,
    *,
    force: bool = False,
) -> None:
    target = Path(path)
    if target.is_dir():
        raise IsADirectoryError(f"Output path must be a file: {target}")
    if target.exists() and not force:
        raise FileExistsError(f"Output already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        if force:
            os.replace(temporary_path, target)
        else:
            try:
                os.link(temporary_path, target)
            except FileExistsError as exc:
                raise FileExistsError(f"Output already exists: {target}") from exc
            temporary_path.unlink()
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def write_json_safely(path: str | Path, payload: dict, *, force: bool = False) -> None:
    write_text_safely(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        force=force,
    )


def escape_ass_text(text: str) -> str:
    # Full-width braces prevent user text from becoming ASS override blocks.
    return (
        text.replace("\\", r"\\")
        .replace("{", "｛")
        .replace("}", "｝")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", r"\N")
    )


def highlight_keywords(text: str, keywords: Sequence[str], color: str = "&H004DD8FF") -> str:
    escaped = escape_ass_text(text)
    for keyword in sorted((kw for kw in keywords if kw), key=len, reverse=True):
        escaped_keyword = escape_ass_text(keyword)
        replacement = r"{\b1\c" + color + "}" + escaped_keyword + r"{\r}"
        escaped = escaped.replace(escaped_keyword, replacement, 1)
    return escaped
