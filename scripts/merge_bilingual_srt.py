#!/usr/bin/env python3
"""merge_bilingual_srt.py — Merge zh-TW + EN SRT into bilingual SRT.

Usage:
    python merge_bilingual_srt.py <zh.srt> <en.srt> <output.srt>

The output SRT will have Chinese as the main line and English as the second line,
sharing the same timestamp (from the Chinese SRT).
"""

import argparse
import os
import re


def parse_srt(path):
    """Parse an SRT file into a list of (index, time_range, text) tuples."""
    with open(path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    blocks = re.split(r'\r?\n\s*\r?\n', content.strip())
    entries = []
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) >= 3 and ' --> ' in lines[1]:
            idx = lines[0].strip()
            time_range = lines[1].strip()
            text = '\n'.join(lines[2:]).strip()
            entries.append((idx, time_range, text))
    return entries


def parse_srt_time(time_str):
    """Parse SRT time string '00:01:23,456' -> total milliseconds."""
    m = re.fullmatch(r'(\d+):([0-5]\d):([0-5]\d)[,.](\d{1,3})', time_str.strip())
    if not m:
        raise ValueError(f"Invalid SRT timestamp: {time_str!r}")
    h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
    ms = int(m.group(4).ljust(3, '0'))
    return h * 3600000 + mi * 60000 + s * 1000 + ms


def time_diff_ms(t1, t2):
    """Return absolute difference in ms between two SRT time ranges.

    Each is 'start --> end' format. Returns max of start diff and end diff.
    """
    s1, e1 = t1.split(' --> ')
    s2, e2 = t2.split(' --> ')
    return max(abs(parse_srt_time(s1) - parse_srt_time(s2)),
               abs(parse_srt_time(e1) - parse_srt_time(e2)))


def merge_bilingual(
    zh_entries,
    en_entries,
    max_time_diff_ms=500,
    min_overlap_ms=250,
    min_overlap_ratio=0.2,
):
    """Merge zh-TW and EN SRT entries, using Chinese timestamps.

    Args:
        zh_entries: List of (index, time_range, text) for Chinese
        en_entries: List of (index, time_range, text) for English
        max_time_diff_ms: Warn if timestamps differ more than this

    Returns:
        List of merged SRT block strings
    """
    merged = []
    groups = [[] for _ in zh_entries]
    unmatched = []
    zh_ranges = []
    for _, time_range, _ in zh_entries:
        start, end = time_range.split(' --> ', 1)
        start_ms, end_ms = parse_srt_time(start), parse_srt_time(end)
        if end_ms <= start_ms:
            raise ValueError(f"SRT end must be after start: {time_range!r}")
        zh_ranges.append((start_ms, end_ms))

    for en_entry in en_entries:
        _, time_range, _ = en_entry
        start, end = time_range.split(' --> ', 1)
        en_start, en_end = parse_srt_time(start), parse_srt_time(end)
        if en_end <= en_start:
            raise ValueError(f"SRT end must be after start: {time_range!r}")
        en_center = (en_start + en_end) / 2
        substantial_indexes = []
        best_index = None
        best_overlap = 0
        best_center_diff = float('inf')
        en_duration = en_end - en_start

        for index, (zh_start, zh_end) in enumerate(zh_ranges):
            overlap = max(0, min(zh_end, en_end) - max(zh_start, en_start))
            center_diff = abs(((zh_start + zh_end) / 2) - en_center)
            zh_duration = zh_end - zh_start
            overlap_ratio = max(overlap / en_duration, overlap / zh_duration)
            if overlap >= min_overlap_ms and overlap_ratio >= min_overlap_ratio:
                substantial_indexes.append(index)
            if overlap > best_overlap or (
                overlap == best_overlap and center_diff < best_center_diff
            ):
                best_index = index
                best_overlap = overlap
                best_center_diff = center_diff

        if substantial_indexes:
            for index in substantial_indexes:
                groups[index].append(en_entry)
        elif best_index is not None and (
            best_overlap > 0 or best_center_diff <= max_time_diff_ms
        ):
            groups[best_index].append(en_entry)
        else:
            unmatched.append(en_entry)

    output_index = 1
    for index, (_, z_time, z_text) in enumerate(zh_entries):
        english_text = '\n'.join(text for _, _, text in groups[index])
        body = f"{z_text}\n{english_text}" if english_text else z_text
        merged.append(f"{output_index}\n{z_time}\n{body}\n")
        output_index += 1

    if unmatched:
        print(
            f"WARNING: {len(unmatched)} English entries had no Chinese time match",
            file=sys.stderr,
        )
        for _, e_time, e_text in unmatched:
            merged.append(f"{output_index}\n{e_time}\n{e_text}\n")
            output_index += 1

    return merged


def main():
    parser = argparse.ArgumentParser(description="Merge zh-TW and English SRT by time overlap")
    parser.add_argument("zh_srt")
    parser.add_argument("en_srt")
    parser.add_argument("output")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output file")
    args = parser.parse_args()
    if os.path.exists(args.output) and not args.force:
        parser.error(f"Output already exists: {args.output}. Use --force to overwrite it.")

    zh = parse_srt(args.zh_srt)
    en = parse_srt(args.en_srt)
    if not zh:
        parser.error(f"No valid subtitle entries found in {args.zh_srt}")
    if not en:
        parser.error(f"No valid subtitle entries found in {args.en_srt}")

    print(f"Chinese SRT: {len(zh)} entries")
    print(f"English SRT: {len(en)} entries")

    result = merge_bilingual(zh, en)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write('\n'.join(result) + '\n')

    print(f"Bilingual SRT saved to {args.output} ({len(result)} entries)")


if __name__ == '__main__':
    main()
