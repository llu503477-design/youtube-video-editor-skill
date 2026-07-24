#!/usr/bin/env python3
"""Validate an Agent-translated SRT against the Whisper source SRT."""

import argparse
from pathlib import Path
import re
import sys
import unicodedata


TIMESTAMP_PATTERN = re.compile(
    r"^(?P<start>\d{2}:\d{2}:\d{2},\d{3}) --> "
    r"(?P<end>\d{2}:\d{2}:\d{2},\d{3})$"
)


def parse_timestamp(value):
    hours, minutes, rest = value.split(":")
    seconds, milliseconds = rest.split(",")
    parts = tuple(map(int, (hours, minutes, seconds, milliseconds)))
    if parts[1] > 59 or parts[2] > 59 or parts[3] > 999:
        raise ValueError(f"Invalid SRT timestamp value: {value!r}.")
    return ((parts[0] * 60 + parts[1]) * 60 + parts[2]) * 1000 + parts[3]


def parse_srt_strict(path):
    try:
        content = Path(path).read_text(encoding="utf-8-sig")
    except OSError as error:
        raise ValueError(f"Cannot read SRT {path}: {error}") from error

    normalized = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise ValueError(f"SRT is empty: {path}")

    entries = []
    expected_index = 1
    for block_number, block in enumerate(re.split(r"\n{2,}", normalized), start=1):
        lines = block.splitlines()
        if len(lines) < 3:
            raise ValueError(
                f"Invalid SRT block {block_number} in {path}: expected index, "
                "timestamp, and text."
            )
        if not lines[0].isdigit():
            raise ValueError(
                f"Invalid SRT cue index in block {block_number}: {lines[0]!r}."
            )
        index = int(lines[0])
        if index != expected_index:
            raise ValueError(
                f"SRT cue sequence changed in {path}: expected {expected_index}, "
                f"found {index}."
            )
        timestamp_match = TIMESTAMP_PATTERN.fullmatch(lines[1])
        if not timestamp_match:
            raise ValueError(
                f"Invalid SRT timestamp in cue {index}: {lines[1]!r}."
            )
        start = parse_timestamp(timestamp_match.group("start"))
        end = parse_timestamp(timestamp_match.group("end"))
        if end <= start:
            raise ValueError(
                f"Invalid SRT timing in cue {index}: end must be after start."
            )
        text = "\n".join(lines[2:])
        if not text.strip():
            raise ValueError(f"Cue {index} has empty text.")
        entries.append((str(index), lines[1], text))
        expected_index += 1
    return entries


def is_english_dominant(text):
    latin_letters = 0
    other_letters = 0
    for character in text:
        if not unicodedata.category(character).startswith("L"):
            continue
        if "LATIN" in unicodedata.name(character, ""):
            latin_letters += 1
        else:
            other_letters += 1
    return latin_letters > 0 and other_letters <= latin_letters * 0.2


def validate_translation(source_entries, translated_entries):
    if len(source_entries) != len(translated_entries):
        raise ValueError(
            "Cue count changed during Agent translation: "
            f"{len(source_entries)} source vs {len(translated_entries)} translated."
        )

    for position, (source, translated) in enumerate(
        zip(source_entries, translated_entries), start=1
    ):
        source_index, source_time, _ = source
        translated_index, translated_time, translated_text = translated
        if translated_index != source_index:
            raise ValueError(
                f"Cue {position} index changed: {source_index!r} -> {translated_index!r}."
            )
        if translated_time != source_time:
            raise ValueError(
                f"Cue {source_index} timestamp changed: "
                f"{source_time!r} -> {translated_time!r}."
            )
        if not translated_text.strip():
            raise ValueError(f"Cue {source_index} has an empty translation.")
        if not is_english_dominant(translated_text):
            raise ValueError(
                f"Cue {source_index} is not English-dominant after Agent translation."
            )


def main():
    parser = argparse.ArgumentParser(
        description="Validate an English SRT translated by the active Agent."
    )
    parser.add_argument("source_srt", help="Whisper source-language SRT")
    parser.add_argument("translated_srt", help="Agent-translated English SRT")
    args = parser.parse_args()

    try:
        source_entries = parse_srt_strict(args.source_srt)
        translated_entries = parse_srt_strict(args.translated_srt)
        validate_translation(source_entries, translated_entries)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        f"Agent translation valid: {len(source_entries)} cues; "
        "indexes and timestamps preserved."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
