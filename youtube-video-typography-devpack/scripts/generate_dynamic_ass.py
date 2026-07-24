#!/usr/bin/env python3
"""Generate styled ASS captions from a visual typography plan."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from typography_core import (
    TEMPLATE_IDS,
    escape_ass_text,
    highlight_keywords,
    load_json,
    seconds_to_ass,
    write_text_safely,
)

STYLE_MAP = {
    "clean-bottom": "Caption",
    "question-pop": "Question",
    "impact-slam": "Impact",
    "warning-alert": "Warning",
    "big-number": "Number",
    "chapter-title": "Chapter",
    "quote-card": "Quote",
    "cta-card": "CTA",
}


def ass_header(width: int, height: int) -> str:
    normal = 62 if height >= 1600 else 42
    emphasized = 84 if height >= 1600 else 58
    margin_v = max(50, int(height * 0.16))
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Caption,Noto Sans TC,{normal},&H00FFFFFF,&H004DD8FF,&H00111111,&H70000000,-1,0,0,0,100,100,0,0,1,6,2,2,70,70,{margin_v},1
Style: Question,Noto Sans TC,{normal + 4},&H00FFFFFF,&H004DD8FF,&H00111111,&H70000000,-1,0,0,0,100,100,0,0,1,7,2,2,70,70,{margin_v},1
Style: Impact,Noto Sans TC,{emphasized},&H004DD8FF,&H00FFFFFF,&H00111111,&H50000000,-1,0,0,0,100,100,0,-2,1,10,4,5,50,50,0,1
Style: Warning,Noto Sans TC,{emphasized},&H00303BFF,&H00FFFFFF,&H00111111,&H50000000,-1,0,0,0,100,100,0,0,1,10,4,5,50,50,0,1
Style: Number,Noto Sans TC,{emphasized},&H004DD8FF,&H00FFFFFF,&H00111111,&H50000000,-1,0,0,0,100,100,0,0,1,9,3,5,50,50,0,1
Style: Chapter,Noto Sans TC,{normal + 10},&H00FFFFFF,&H004DD8FF,&H00111111,&H80000000,-1,0,0,0,100,100,0,0,3,3,0,8,80,80,120,1
Style: Quote,Noto Sans TC,{normal},&H00FFFFFF,&H004DD8FF,&H00111111,&H70000000,0,-1,0,0,100,100,0,0,1,5,2,2,80,80,{margin_v},1
Style: CTA,Noto Sans TC,{emphasized - 6},&H00FFFFFF,&H004DD8FF,&H00111111,&H803030FF,-1,0,0,0,100,100,0,0,3,3,0,5,60,60,0,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""


def event_override(event: dict, width: int, height: int) -> str:
    template = event["templateId"]
    duration_ms = max(1, int((float(event["end"]) - float(event["start"])) * 1000))
    center_x = width // 2
    center_y = int(height * 0.46)

    if template == "impact-slam":
        return (
            rf"{{\an5\pos({center_x},{center_y})\fad(70,120)"
            rf"\fscx125\fscy125\t(0,{min(220, duration_ms)},\fscx100\fscy100)"
            rf"\frz-2}}"
        )
    if template == "warning-alert":
        return (
            rf"{{\an5\pos({center_x},{center_y})\fad(70,120)"
            rf"\fscx115\fscy115\t(0,{min(180, duration_ms)},\fscx100\fscy100)}}"
        )
    if template == "big-number":
        return (
            rf"{{\an5\pos({center_x},{center_y})\fad(90,120)"
            rf"\fscx110\fscy110\t(0,{min(180, duration_ms)},\fscx100\fscy100)}}"
        )
    if template == "chapter-title":
        return r"{\fad(140,180)}"
    if template == "cta-card":
        return (
            rf"{{\an5\pos({center_x},{int(height * 0.55)})\fad(100,150)"
            rf"\fscx108\fscy108\t(0,{min(180, duration_ms)},\fscx100\fscy100)}}"
        )
    if template == "question-pop":
        return r"{\fad(80,100)}"
    return r"{\fad(80,80)}"


def generate_ass(plan: dict) -> str:
    project = plan.get("project", {})
    width = int(project.get("width", 1080))
    height = int(project.get("height", 1920))
    lines = [ass_header(width, height).rstrip()]

    for event in plan.get("events", []):
        template = event.get("templateId", "")
        if template not in TEMPLATE_IDS:
            raise ValueError(f"Unknown templateId: {template!r}")
        style = STYLE_MAP[template]
        start = seconds_to_ass(float(event["start"]))
        end = seconds_to_ass(float(event["end"]))
        keywords = event.get("keywords") or []
        if keywords:
            text = highlight_keywords(str(event["text"]), keywords)
        else:
            text = escape_ass_text(str(event["text"]))
        text = event_override(event, width, height) + text
        lines.append(f"Dialogue: 0,{start},{end},{style},,0,0,0,,{text}")

    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_plan", type=Path)
    parser.add_argument("output_ass", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.input_plan.resolve() == args.output_ass.resolve():
            raise ValueError("Input visual plan and output ASS must use different paths")
        plan = load_json(args.input_plan)
        output = generate_ass(plan)
        write_text_safely(args.output_ass, output, force=args.force)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"generate-dynamic-ass: {exc}", file=sys.stderr)
        return 1

    print(f"Created ASS: {args.output_ass}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
