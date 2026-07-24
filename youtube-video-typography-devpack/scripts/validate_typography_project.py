#!/usr/bin/env python3
"""Validate visual typography plan contracts and quality budgets."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from typography_core import (
    CAPTION_RULES,
    EFFECT_BUDGET,
    TEMPLATE_IDS,
    effect_budget_violations,
    is_finite_number,
    load_json,
    write_text_safely,
)

HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
PURPOSES = {
    "normal_dialogue",
    "important_fact",
    "number",
    "warning",
    "question",
    "answer",
    "punchline",
    "chapter_title",
    "quotation",
    "call_to_action",
}
READING_PRIORITIES = {"low", "normal", "high"}
TOP_LEVEL_KEYS = {"schemaVersion", "project", "brandId", "events"}
PROJECT_KEYS = {"width", "height", "fps", "duration", "language"}
EVENT_KEYS = {
    "id",
    "start",
    "end",
    "text",
    "purpose",
    "emotion",
    "intensity",
    "keywords",
    "templateId",
    "strongEffect",
    "readingPriority",
    "words",
}


def validate_plan(plan: Any) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(plan, dict):
        return {
            "valid": False,
            "errors": ["visual plan root must be an object"],
            "warnings": [],
            "metrics": {"eventCount": 0, "strongEffectCount": 0},
        }

    if plan.get("schemaVersion") != "1.0":
        errors.append("schemaVersion must be '1.0'")
    extra_top_level = sorted(set(plan) - TOP_LEVEL_KEYS)
    if extra_top_level:
        errors.append(f"unknown top-level properties: {', '.join(extra_top_level)}")
    if "brandId" in plan and not isinstance(plan["brandId"], str):
        errors.append("brandId must be a string")

    project = plan.get("project")
    if not isinstance(project, dict):
        errors.append("project must be an object")
        project = {}
    extra_project = sorted(set(project) - PROJECT_KEYS)
    if extra_project:
        errors.append(f"unknown project properties: {', '.join(extra_project)}")

    width = project.get("width")
    height = project.get("height")
    fps = project.get("fps")
    duration = project.get("duration")

    if not isinstance(width, int) or isinstance(width, bool) or width < 16:
        errors.append("project.width must be an integer >= 16")
    if not isinstance(height, int) or isinstance(height, bool) or height < 16:
        errors.append("project.height must be an integer >= 16")
    if not is_finite_number(fps) or fps <= 0:
        errors.append("project.fps must be > 0")
    if (
        not is_finite_number(duration)
        or duration <= 0
    ):
        errors.append("project.duration must be > 0")
        duration = 0
    language = project.get("language")
    if not isinstance(language, str) or len(language) < 2:
        errors.append("project.language must be a string with at least 2 characters")

    events = plan.get("events")
    if not isinstance(events, list) or not events:
        errors.append("events must be a non-empty array")
        events = []

    seen_ids: set[str] = set()
    previous_start: float | None = None
    previous_end: float | None = None
    caption_config = CAPTION_RULES.get("caption", {})
    minimum_duration = float(caption_config.get("minimumDurationMs", 650)) / 1000
    maximum_duration = float(caption_config.get("maximumDurationMs", 3200)) / 1000
    maximum_lines = int(caption_config.get("maxLines", 2))

    for position, event in enumerate(events):
        prefix = f"events[{position}]"
        if not isinstance(event, dict):
            errors.append(f"{prefix} must be an object")
            continue
        extra_event = sorted(set(event) - EVENT_KEYS)
        if extra_event:
            errors.append(f"{prefix} has unknown properties: {', '.join(extra_event)}")

        event_id = event.get("id")
        if not isinstance(event_id, str) or not event_id:
            errors.append(f"{prefix}.id must be non-empty")
        elif event_id in seen_ids:
            errors.append(f"{prefix}.id is duplicated: {event_id}")
        else:
            seen_ids.add(event_id)

        start = event.get("start")
        end = event.get("end")
        if (
            not is_finite_number(start)
            or start < 0
        ):
            errors.append(f"{prefix}.start must be >= 0")
            continue
        if (
            not is_finite_number(end)
            or end <= start
        ):
            errors.append(f"{prefix}.end must be greater than start")
            continue
        if duration and end > duration + 0.001:
            errors.append(f"{prefix}.end exceeds project duration")
        event_duration = float(end) - float(start)
        if event_duration < minimum_duration:
            warnings.append(
                f"{prefix} duration must be at least {minimum_duration:.3f}s"
            )
        if event_duration > maximum_duration:
            warnings.append(
                f"{prefix} duration must be at most {maximum_duration:.3f}s"
            )
        if previous_start is not None and float(start) < previous_start:
            errors.append(f"{prefix}.start is earlier than the previous event")
        if previous_end is not None and float(start) < previous_end:
            warnings.append(f"{prefix} overlaps the previous event")
        previous_start = float(start)
        previous_end = float(end)

        text = event.get("text")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{prefix}.text must be non-empty")
        else:
            line_count = len(text.replace("\r", "").split("\n"))
            if line_count > maximum_lines:
                errors.append(
                    f"{prefix}.text must have at most {maximum_lines} lines"
                )
            compact_length = len(re.sub(r"\s+", "", text))
            if compact_length > 36:
                warnings.append(f"{prefix}.text may be too dense ({compact_length} chars)")

        template = event.get("templateId")
        if template not in TEMPLATE_IDS:
            errors.append(f"{prefix}.templateId is unknown: {template!r}")

        purpose = event.get("purpose")
        if purpose not in PURPOSES:
            errors.append(f"{prefix}.purpose is unknown: {purpose!r}")
        emotion = event.get("emotion")
        if not isinstance(emotion, str):
            errors.append(f"{prefix}.emotion must be a string")
        keywords = event.get("keywords")
        if not isinstance(keywords, list) or not all(
            isinstance(keyword, str) for keyword in keywords
        ):
            errors.append(f"{prefix}.keywords must be an array of strings")
        if not isinstance(event.get("strongEffect"), bool):
            errors.append(f"{prefix}.strongEffect must be a boolean")
        reading_priority = event.get("readingPriority")
        if reading_priority not in READING_PRIORITIES:
            errors.append(
                f"{prefix}.readingPriority is unknown: {reading_priority!r}"
            )

        intensity = event.get("intensity")
        if (
            not is_finite_number(intensity)
            or not 0 <= intensity <= 1
        ):
            errors.append(f"{prefix}.intensity must be between 0 and 1")

        words = event.get("words")
        if words is not None:
            if not isinstance(words, list):
                errors.append(f"{prefix}.words must be an array")
            else:
                for word_position, word in enumerate(words):
                    word_prefix = f"{prefix}.words[{word_position}]"
                    if not isinstance(word, dict):
                        errors.append(f"{word_prefix} must be an object")
                        continue
                    if not isinstance(word.get("text"), str):
                        errors.append(f"{word_prefix}.text must be a string")
                    missing_word_keys = sorted(
                        {"text", "start", "end"} - set(word)
                    )
                    if missing_word_keys:
                        errors.append(
                            f"{word_prefix} missing required properties: "
                            f"{', '.join(missing_word_keys)}"
                        )
                    word_start = word.get("start")
                    word_end = word.get("end")
                    if (
                        not is_finite_number(word_start)
                        or word_start < 0
                    ):
                        errors.append(f"{word_prefix}.start must be >= 0")
                    if (
                        not is_finite_number(word_end)
                        or not is_finite_number(word_start)
                        or word_end < word_start
                    ):
                        errors.append(
                            f"{word_prefix}.end must be greater than or equal to start"
                        )

    budget_window = float(EFFECT_BUDGET["windowSeconds"])
    max_strong = int(EFFECT_BUDGET["strongEffects"])
    for violation in effect_budget_violations(
        events,
        window_seconds=budget_window,
        max_strong=max_strong,
    ):
        ids = ", ".join(str(event.get("id", "?")) for event in violation)
        errors.append(
            f"effect budget exceeded within {budget_window:g}s "
            f"({len(violation)} strong effects): {ids}"
        )

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "eventCount": len(events),
            "strongEffectCount": sum(
                1 for event in events if isinstance(event, dict) and event.get("strongEffect") is True
            ),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_plan", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.report and args.input_plan.resolve() == args.report.resolve():
            raise ValueError("Input visual plan and QA report must use different paths")
        plan = load_json(args.input_plan)
        report = validate_plan(plan)
        payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"

        if args.report:
            write_text_safely(args.report, payload, force=args.force)
        else:
            print(payload, end="")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"validate-typography-project: {exc}", file=sys.stderr)
        return 2

    if report["valid"]:
        print(
            f"Typography plan valid: {report['metrics']['eventCount']} events",
            file=sys.stderr,
        )
        return 0

    for error in report["errors"]:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
