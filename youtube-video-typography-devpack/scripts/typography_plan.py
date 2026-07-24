#!/usr/bin/env python3
"""Create a deterministic visual typography plan from an SRT file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from typography_core import build_visual_plan, parse_srt_file, write_json_safely


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_srt", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--language", default="zh-TW")
    parser.add_argument("--brand-id", default="default-zh-tw")
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.input_srt.resolve() == args.output_json.resolve():
            raise ValueError("Input SRT and output JSON must use different paths")
        cues = parse_srt_file(args.input_srt)
        plan = build_visual_plan(
            cues,
            width=args.width,
            height=args.height,
            fps=args.fps,
            language=args.language,
            brand_id=args.brand_id,
        )
        write_json_safely(args.output_json, plan, force=args.force)
    except (OSError, ValueError) as exc:
        print(f"typography-plan: {exc}", file=sys.stderr)
        return 1

    print(f"Created visual plan: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
