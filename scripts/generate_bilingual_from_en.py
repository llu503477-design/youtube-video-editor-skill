#!/usr/bin/env python3
"""generate_bilingual_from_en.py — [DEPRECATED v1.2] Use two-stage Whisper instead.

Pipeline (deprecated):
  1. Extract audio from video (or use existing WAV)
  2. Transcribe English with faster-whisper → English SRT
  3. Translate EN text to zh-CN using HuggingFace MarianMT
  4. Convert zh-CN → zh-TW using OpenCC
  5. Generate bilingual ASS (zh-TW 24px + EN 18px) or merged SRT

Usage:
  python generate_bilingual_from_en.py <video.mp4> [--output <dir>] [--ass]
  python generate_bilingual_from_en.py --audio <audio.wav> [--output <dir>] [--ass]

Requirements:
  pip install faster-whisper transformers sentencepiece opencc-python-reimplemented

Author: YouTube Video Editor Skill
Version: 1.0.0
"""

import os
import sys
import argparse
import subprocess
import tempfile
import unicodedata
from pathlib import Path


# ── Step 1: Extract Audio ──────────────────────────────────────────────

def extract_audio(video_path: str, output_wav: str) -> str:
    """Extract 16kHz mono WAV from video file using FFmpeg."""
    print(f"[1/5] Extracting audio: {video_path} → {output_wav}")
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        "-y", output_wav
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"       Audio extracted: {output_wav}")
    return output_wav


# ── Step 2: Transcribe English ─────────────────────────────────────────

def transcribe_english(wav_path: str, model_size: str = "base") -> list:
    """Transcribe English audio with faster-whisper.

    Returns list of (start_sec, end_sec, text).
    """
    print(f"[2/5] Transcribing English (faster-whisper, model={model_size})...")
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(wav_path, language="en", beam_size=5)

    entries = []
    for seg in segments:
        entries.append((seg.start, seg.end, seg.text.strip()))

    print(f"       Transcribed: {len(entries)} segments")
    return entries


# ── Step 3: Write SRT ──────────────────────────────────────────────────

def write_srt(entries: list, srt_path: str):
    """Write entries to SRT file."""
    def fmt_time(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int((sec - int(sec)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, (start, end, text) in enumerate(entries, 1):
            if text:
                f.write(f"{i}\n{fmt_time(start)} --> {fmt_time(end)}\n{text}\n\n")

    print(f"       SRT written: {srt_path} ({len(entries)} entries)")


# ── Step 4: Translate EN → zh-CN using MarianMT ────────────────────────

def translate_to_zh_cn(entries: list, batch_size: int = 16) -> list:
    """Translate English entries to Simplified Chinese using MarianMT.

    Returns list of (start, end, zh_text).
    """
    print(f"[3/5] Translating EN → zh-CN (MarianMT)...")
    from transformers import MarianMTModel, MarianTokenizer

    model_name = "Helsinki-NLP/opus-mt-en-zh"
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)

    zh_entries = []
    texts = [text for _, _, text in entries]

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        inputs = tokenizer(batch, return_tensors="pt", padding=True,
                          truncation=True, max_length=128)
        translated = model.generate(**inputs)
        zh_batch = [tokenizer.decode(t, skip_special_tokens=True) for t in translated]

        for j, zh_text in enumerate(zh_batch):
            idx = i + j
            zh_entries.append((entries[idx][0], entries[idx][1], zh_text))

        progress = min(i + batch_size, len(texts))
        print(f"       Translated: {progress}/{len(texts)}", end="\r")

    print(f"\n       Translation complete: {len(zh_entries)} entries")
    return zh_entries


# ── Step 5: Convert zh-CN → zh-TW using OpenCC ─────────────────────────

def convert_to_traditional(entries: list) -> list:
    """Convert Simplified Chinese to Traditional Chinese using OpenCC."""
    print(f"[4/5] Converting zh-CN → zh-TW (OpenCC)...")
    from opencc import OpenCC

    cc = OpenCC("s2t")  # Simplified → Traditional

    tw_entries = []
    for start, end, text in entries:
        tw_text = cc.convert(text)
        tw_entries.append((start, end, tw_text))

    # Count CJK characters to verify
    cjk_count = sum(
        1 for c in "".join(t for _, _, t in tw_entries)
        if '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf'
    )
    print(f"       Converted: {len(tw_entries)} entries, {cjk_count} CJK chars")
    return tw_entries


# ── Step 6: Generate Bilingual ASS ─────────────────────────────────────

ASS_HEADER = """[Script Info]
; Script generated by generate_bilingual_from_en.py
; Font: zh-TW=48px, EN=36px (1.8x), BorderStyle=4 opaque background
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: zh-TW,Noto Sans CJK SC,48,&H00FFFFFF,&H000000FF,&H00000000,&HFF000000,1,0,0,0,100,100,0,0,4,1,1,2,40,40,50,1
Style: EN,Arial,36,&H00FFFFFF,&H000000FF,&H00000000,&HFF000000,0,0,0,0,100,100,0,0,4,1,1,2,40,40,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def generate_bilingual_ass(zh_entries: list, en_entries: list, ass_path: str):
    """Generate bilingual ASS with zh-TW (24px) + EN (18px)."""
    print(f"[5/5] Generating bilingual ASS: {ass_path}")

    def srt_time_to_ass(st: float) -> str:
        h = int(st // 3600)
        m = int((st % 3600) // 60)
        s = st % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    lines = [ASS_HEADER]
    min_len = min(len(zh_entries), len(en_entries))

    for i in range(min_len):
        zh_start, zh_end, zh_text = zh_entries[i]
        en_start, en_end, en_text = en_entries[i]

        # Use zh-TW timestamps
        start = srt_time_to_ass(zh_start)
        end = srt_time_to_ass(zh_end)

        lines.append(
            f"Dialogue: 0,{start},{end},zh-TW,,0,0,0,,"
            f"{zh_text}\\N{{\\rEN}}{en_text}"
        )

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"       ASS saved: {ass_path} ({min_len} entries)")
    print(f"         zh-TW style: Noto Sans CJK SC, 24px (main)")
    print(f"         EN style: Arial, 18px (secondary)")


def generate_bilingual_srt(zh_entries: list, en_entries: list, srt_path: str):
    """Generate merged bilingual SRT (zh-TW main + EN secondary)."""
    print(f"[5/5] Generating bilingual SRT: {srt_path}")

    def fmt_time(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int((sec - int(sec)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    min_len = min(len(zh_entries), len(en_entries))
    with open(srt_path, "w", encoding="utf-8") as f:
        for i in range(min_len):
            zh_start, zh_end, zh_text = zh_entries[i]
            _, _, en_text = en_entries[i]
            f.write(f"{i+1}\n")
            f.write(f"{fmt_time(zh_start)} --> {fmt_time(zh_end)}\n")
            f.write(f"{zh_text}\n{en_text}\n\n")


# ── Main ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate zh-TW + EN bilingual subtitles from English video"
    )
    parser.add_argument("input", nargs="?", help="Input video file (.mp4, .mkv, etc.)")
    parser.add_argument("--audio", help="Input audio file (skip video extraction)")
    parser.add_argument("--output", "-o", default="output", help="Output directory")
    parser.add_argument("--ass", action="store_true", default=True,
                       help="Generate ASS format (default)")
    parser.add_argument("--srt", action="store_true",
                       help="Generate merged SRT format instead of ASS")
    parser.add_argument("--model", default="base",
                       choices=["tiny", "base", "small", "medium"],
                       help="Whisper model size (default: base)")
    parser.add_argument("--no-burn", action="store_true",
                       help="Skip burning subtitles into video")
    parser.add_argument("--drawbox", action="store_true", default=False,
                       help="Draw black background bar (y=ih-200:h=200) to cover hardcoded subs")
    parser.add_argument("--box-height", type=int, default=200,
                       help="Black bar height in pixels for --drawbox (default: 200)")

    args = parser.parse_args()

    # Determine input
    if not args.input and not args.audio:
        parser.print_help()
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)

    # Step 1: Audio extraction
    if args.audio:
        wav_path = args.audio
    else:
        wav_path = os.path.join(args.output, "audio_raw.wav")
        if not os.path.exists(wav_path):
            extract_audio(args.input, wav_path)
        else:
            print(f"[1/5] Using existing audio: {wav_path}")

    # Step 2: Transcribe English
    srt_en = os.path.join(args.output, "subs_en.srt")
    en_entries = transcribe_english(wav_path, model_size=args.model)
    write_srt(en_entries, srt_en)

    # Step 3: Translate EN → zh-CN
    zh_cn_entries = translate_to_zh_cn(en_entries)

    # Step 4: Convert zh-CN → zh-TW
    zh_tw_entries = convert_to_traditional(zh_cn_entries)

    # Step 5: Write Chinese SRT
    srt_zh = os.path.join(args.output, "subs_zh_tw.srt")
    write_srt(zh_tw_entries, srt_zh)

    # Step 6: Generate bilingual output
    if args.srt:
        bilingual_path = os.path.join(args.output, "bilingual.srt")
        generate_bilingual_srt(zh_tw_entries, en_entries, bilingual_path)
    else:
        bilingual_path = os.path.join(args.output, "bilingual.ass")
        generate_bilingual_ass(zh_tw_entries, en_entries, bilingual_path)

    # Step 7: Burn into video (optional)
    if args.input and not args.no_burn:
        base, ext = os.path.splitext(os.path.basename(args.input))
        output_video = os.path.join(args.output, f"{base}_zhTW_EN.mp4")

        print(f"\n[Bonus] Burning subtitles into video...")
        print(f"  Input:  {args.input}")
        print(f"  Output: {output_video}")

        ass_path_esc = bilingual_path.replace(os.sep, '/')

        if args.drawbox:
            # Draw full-width black bar to cover hardcoded subs, then overlay ASS
            bh = args.box_height
            filter_str = (
                f"drawbox=x=0:y=ih-{bh}:w=iw:h={bh}:color=black@1:t=fill,"
                f"ass={ass_path_esc}"
            )
            print(f"  - drawbox enabled: black bar height={bh}px")
        elif args.srt:
            # SRT burn with force_style
            filter_str = (
                f"subtitles={ass_path_esc}"
                f":force_style='FontName=Arial,FontSize=48,"
                f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                f"BackColour=&HFF000000,Outline=1,BorderStyle=4'"
            )
        else:
            # ASS burn
            filter_str = f"ass={ass_path_esc}"

        cmd = [
            "ffmpeg", "-i", args.input,
            "-vf", filter_str,
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-y", output_video
        ]
        subprocess.run(cmd, check=True)
        print(f"  ✓ Video saved: {output_video}")

    print("\n✓ Pipeline complete!")


if __name__ == "__main__":
    main()
