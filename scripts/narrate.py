#!/usr/bin/env python3
"""narrate.py — Generate video narration from subtitles.

Transforms subtitle text into spoken narration using Edge-TTS.
Supports three modes: intro (stage-by-stage), full (read-aloud), summary.

Usage:
    # From subtitles (recommended)
    python narrate.py --subs subtitles.srt --lang zh-TW --output narration.wav

    # Specify voice and mode
    python narrate.py --subs subs.srt --lang zh-TW --mode intro --voice zh-TW-HsiaoChenNeural --output out.wav

    # From custom script (one line per segment)
    python narrate.py --script script.txt --lang en --voice en-US-AriaNeural --output out.wav

    # With timing offset and inter-segment pause
    python narrate.py --subs subs.srt --lang zh-TW --offset 2000 --pause 300 --output narration.wav

Language codes for --lang:
    zh-TW, zh-CN, en, ja, ko, etc. (must match available Edge-TTS voices)
"""

import sys
import os
import re
import subprocess
import tempfile
import argparse
from pathlib import Path


# ── Intro Templates (per-segment stage guide) ──
INTRO_ZH_TW = [
    "歡迎收看，首先我們來看看{summary}",
    "接下來讓我們了解一下{summary}",
    "現在進一步探討{summary}",
    "另一方面，我們看到{summary}",
    "接下來這個重點是{summary}",
    "最後關鍵的一點是{summary}",
    "總結來說，{summary}",
]

INTRO_EN = [
    "Welcome! First, let's look at {summary}",
    "Next, let's understand {summary}",
    "Now let's dive deeper into {summary}",
    "On the other hand, we see {summary}",
    "Another important point is {summary}",
    "A key point to note is {summary}",
    "In conclusion, {summary}",
]

# Default Edge-TTS voices per language
DEFAULT_VOICES = {
    "zh-TW": "zh-TW-HsiaoChenNeural",
    "zh-CN": "zh-CN-XiaoxiaoNeural",
    "en": "en-US-AriaNeural",
    "en-US": "en-US-AriaNeural",
    "en-GB": "en-GB-SoniaNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
}


def parse_srt(path):
    """Parse SRT into list of (start_ms, end_ms, text)."""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = content.strip().split('\n\n')
    entries = []

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue

        time_line = lines[1].strip()
        text = '\n'.join(lines[2:]).strip()

        # Parse time range: 00:01:23,456 --> 00:01:25,789
        m = re.match(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)', time_line)
        if not m:
            continue

        groups = [int(x) for x in m.groups()]
        start_ms = (groups[0] * 3600 + groups[1] * 60 + groups[2]) * 1000 + groups[3]
        end_ms = (groups[4] * 3600 + groups[5] * 60 + groups[6]) * 1000 + groups[7]

        # Clean text: remove HTML tags, newlines
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('\n', ' ').strip()

        if text:
            entries.append((start_ms, end_ms, text))

    return entries


def parse_script(path):
    """Read plain text script (one paragraph per segment)."""
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.read().strip().split('\n')
    return [line.strip() for line in lines if line.strip()]


def make_summary(text, max_chars=60):
    """Summarize subtitle text to a short phrase for intro templates."""
    # Take first sentence or truncate
    text = text.strip()
    # Remove speaker labels like "John: " or "（男聲）"
    text = re.sub(r'^[\(（]?[^）\)]+[\)）][：:]?\s*', '', text)
    # Take first sentence
    for sep in ['。', '！', '？', '.', '!', '?', '\n']:
        parts = text.split(sep, 1)
        if len(parts) > 1:
            text = parts[0] + sep
            break
    # Truncate
    if len(text) > max_chars:
        text = text[:max_chars].rstrip('，,') + '…'
    return text


def get_intro_templates(lang):
    """Get intro template list for the given language."""
    if lang.startswith("zh"):
        return INTRO_ZH_TW
    else:
        return INTRO_EN


def generate_narration_lines(entries, mode, lang):
    """Generate narration text lines from subtitle entries.

    Args:
        entries: List of (start_ms, end_ms, text)
        mode: "intro", "full", or "summary"
        lang: Language code

    Returns:
        List of (text, start_ms) tuples for narration
    """
    templates = get_intro_templates(lang)
    result = []

    for i, (start_ms, end_ms, text) in enumerate(entries):
        if mode == "intro":
            # Template-based introduction
            tmpl = templates[i % len(templates)]
            summary = make_summary(text)
            narration = tmpl.format(summary=summary)
            result.append((narration, start_ms))

        elif mode == "full":
            # Read original text directly
            result.append((text, start_ms))

        elif mode == "summary":
            # Short summary only
            summary = make_summary(text, max_chars=40)
            result.append((summary, start_ms))

    return result


def run_edge_tts(text, voice, output_path):
    """Run edge-tts to synthesize speech for a text segment.

    Returns True on success.
    """
    cmd = [
        sys.executable, "-m", "edge_tts",
        "--voice", voice,
        "--text", text,
        "--write-media", output_path,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ERROR: edge-tts failed: {e.stderr.decode('utf-8', errors='replace')[:200]}",
              file=sys.stderr)
        return False
    except FileNotFoundError:
        print("  ERROR: edge-tts not installed. Run: pip install edge-tts", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("  ERROR: edge-tts timed out", file=sys.stderr)
        return False


def get_audio_duration(wav_path):
    """Get duration of a WAV file in milliseconds using FFprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", wav_path],
            capture_output=True, text=True, timeout=30
        )
        return int(float(result.stdout.strip()) * 1000)
    except (ValueError, subprocess.TimeoutExpired, FileNotFoundError):
        return 0


def concat_wavs(temp_dir, output_path, sample_rate=24000):
    """Concatenate all WAV files in temp_dir into one output WAV using FFmpeg."""
    wav_files = sorted([
        f for f in os.listdir(temp_dir)
        if f.endswith('.wav') and f.startswith('seg_')
    ], key=lambda x: int(re.search(r'\d+', x).group()))

    if not wav_files:
        print("ERROR: No WAV segments generated", file=sys.stderr)
        return False

    # Create concat list
    list_path = os.path.join(temp_dir, "concat_list.txt")
    with open(list_path, 'w', encoding='utf-8') as f:
        for wav in wav_files:
            f.write(f"file '{os.path.join(temp_dir, wav)}'\n")

    # Use FFmpeg concat demuxer
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_path,
        "-c", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", "1",
        output_path,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: FFmpeg concat failed: {e.stderr.decode('utf-8', errors='replace')[:300]}",
              file=sys.stderr)
        return False


def add_silence_before(wav_path, silence_ms, sample_rate=24000):
    """Prepend silence to a WAV file using FFmpeg."""
    if silence_ms <= 0:
        return True

    temp_path = wav_path + ".tmp.wav"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"anullsrc=r={sample_rate}:cl=mono:d={silence_ms/1000:.3f}",
        "-i", wav_path,
        "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1",
        "-c", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", "1",
        temp_path,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        os.replace(temp_path, wav_path)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  WARNING: silence prepend failed: {e.stderr.decode('utf-8', errors='replace')[:200]}",
              file=sys.stderr)
        try:
            os.remove(temp_path)
        except OSError:
            pass
        return False


def generate_narration_srt(segment_timings, initial_offset=0):
    """Generate SRT entries aligned to actual narration audio timing.

    Each segment timing stores the silence actually prepended to that segment.
    Concatenation then places speech at cumulative duration + segment delay.

    Args:
        segment_timings: List of (requested_start_ms, delay_ms, duration_ms, text)
        initial_offset: Kept for backward compatibility; delays already include it.

    Returns:
        List of (start_ms, end_ms, text) for SRT output
    """
    entries = []
    cumulative_wav = 0  # position in concatenated WAV

    for start_ms, delay_ms, duration_ms, text in segment_timings:
        # This segment's WAV = [silence: delay_ms] + [speech: duration_ms].
        speech_start = cumulative_wav + delay_ms
        speech_end = speech_start + duration_ms

        entries.append((speech_start, speech_end, text))

        cumulative_wav += delay_ms + duration_ms

    # Merge adjacent entries (if they overlap — shouldn't with our calculation)
    # and ensure minimum 1s gap between distinct entries
    merged = []
    for start, end, text in entries:
        if start < end:  # valid entry
            if merged and start - merged[-1][1] < 100:
                # Extend previous if overlapping or too close
                prev_start, prev_end, prev_text = merged.pop()
                merged.append((prev_start, end, prev_text + " " + text))
            else:
                merged.append((start, end, text))

    return merged


def ms_to_srt_time(ms):
    """Convert milliseconds to SRT time format H:MM:SS,mmm."""
    total_sec = ms / 1000
    h = int(total_sec // 3600)
    m = int((total_sec % 3600) // 60)
    s = int(total_sec % 60)
    ms_remain = int(ms % 1000)
    return f"{h:01d}:{m:02d}:{s:02d},{ms_remain:03d}"


def write_srt(entries, output_path):
    """Write SRT file from list of (start_ms, end_ms, text) entries."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, (start_ms, end_ms, text) in enumerate(entries, 1):
            f.write(f"{i}\n")
            f.write(f"{ms_to_srt_time(start_ms)} --> {ms_to_srt_time(end_ms)}\n")
            f.write(f"{text}\n\n")


def main():
    parser = argparse.ArgumentParser(
        description="Generate video narration from subtitles using Edge-TTS"
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--subs", help="SRT subtitle file")
    input_group.add_argument("--script", help="Plain text narration script (one line per segment)")

    parser.add_argument("--output", "-o", default="narration.wav", help="Output WAV file")
    parser.add_argument("--lang", default="zh-TW", help="Narration language (zh-TW, en, ja, etc.)")
    parser.add_argument("--voice", help="Edge-TTS voice (default: auto-detect from --lang)")
    parser.add_argument("--mode", choices=["intro", "full", "summary"], default="intro",
                        help="intro=stage-by-stage, full=read original, summary=short (default: intro)")
    parser.add_argument("--offset", type=int, default=2000,
                        help="Delay in ms before narration starts (default: 2000)")
    parser.add_argument("--pause", type=int, default=200,
                        help="Extra pause in ms between narration segments (default: 200)")
    parser.add_argument("--sample-rate", type=int, default=24000, help="Output sample rate")
    parser.add_argument("--output-subs", help="Generate SRT subtitles aligned to narration audio timing")
    parser.add_argument("--output-subs-lang", default="zh-TW",
                        help="Language for narration subtitles (default: zh-TW)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing --output and --output-subs files")
    parser.add_argument("--allow-partial", action="store_true",
                        help="Keep successful segments and insert silence for failed TTS segments")

    args = parser.parse_args()
    if args.offset < 0:
        parser.error("--offset must be zero or greater")
    if args.pause < 0:
        parser.error("--pause must be zero or greater")
    if args.sample_rate <= 0:
        parser.error("--sample-rate must be greater than zero")
    for output_path in (args.output, args.output_subs):
        if output_path and os.path.exists(output_path) and not args.force:
            parser.error(f"Output already exists: {output_path}. Use --force to overwrite it.")
    if args.output_subs and os.path.abspath(args.output) == os.path.abspath(args.output_subs):
        parser.error("--output and --output-subs must be different files")

    # Resolve voice
    voice = args.voice or DEFAULT_VOICES.get(args.lang)
    if not voice:
        print(f"ERROR: No default voice for '{args.lang}'. Use --voice to specify.", file=sys.stderr)
        sys.exit(1)

    # Load input
    if args.subs:
        print(f"Loading subtitles: {args.subs}")
        entries = parse_srt(args.subs)
        if not entries:
            print("ERROR: No valid entries found in SRT", file=sys.stderr)
            sys.exit(1)
        print(f"  Found {len(entries)} subtitle segments")

        # Generate narration lines
        narration_lines = generate_narration_lines(entries, args.mode, args.lang)

    else:  # --script
        print(f"Loading script: {args.script}")
        lines = parse_script(args.script)
        if not lines:
            print("ERROR: No lines found in script", file=sys.stderr)
            sys.exit(1)
        # For scripts, distribute evenly across a fake 30s-per-segment timeline
        narration_lines = [(line, i * 30000) for i, line in enumerate(lines)]

    print(f"Narration language: {args.lang}")
    print(f"Voice: {voice}")
    print(f"Mode: {args.mode}")
    print(f"Total narration segments: {len(narration_lines)}")
    print()

    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="narration_")

    # Generate TTS for each segment
    success_count = 0
    segment_timings = []
    timeline_ms = 0

    for i, (text, start_ms) in enumerate(narration_lines):
        seg_path = os.path.join(temp_dir, f"seg_{i:04d}.wav")
        print(f"  [{i+1}/{len(narration_lines)}] TTS: {text[:60]}...", end=" ")

        if run_edge_tts(text, voice, seg_path):
            duration_ms = get_audio_duration(seg_path)
            desired_start = max(0, start_ms + args.offset)
            minimum_gap = args.pause if i > 0 else 0
            delay_ms = max(minimum_gap, desired_start - timeline_ms)
            if delay_ms > 0 and not add_silence_before(seg_path, delay_ms, args.sample_rate):
                if not args.allow_partial:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    print("ERROR: Failed to align a narration segment.", file=sys.stderr)
                    sys.exit(1)
                try:
                    os.remove(seg_path)
                except OSError:
                    pass
                print("SKIPPED: alignment failed", file=sys.stderr)
                continue
            speech_start = timeline_ms + delay_ms
            segment_timings.append((start_ms, delay_ms, duration_ms, text))
            timeline_ms = speech_start + duration_ms
            print(f"OK ({duration_ms}ms)")
            success_count += 1
        else:
            print("FAILED")
            if not args.allow_partial:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                print("ERROR: TTS failed. Re-run with --allow-partial to keep a partial result.",
                      file=sys.stderr)
                sys.exit(1)
            # Create a short silent segment as placeholder
            silence_path = seg_path
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", f"anullsrc=r={args.sample_rate}:cl=mono:d=3.0",
                "-c", "pcm_s16le", silence_path
            ], check=True, capture_output=True, timeout=30)
            desired_start = max(0, start_ms + args.offset)
            minimum_gap = args.pause if i > 0 else 0
            delay_ms = max(minimum_gap, desired_start - timeline_ms)
            if delay_ms > 0 and not add_silence_before(silence_path, delay_ms, args.sample_rate):
                print("ERROR: Failed to align placeholder audio", file=sys.stderr)
                sys.exit(1)
            segment_timings.append((start_ms, delay_ms, 3000, f"[FAILED] {text}"))
            timeline_ms += delay_ms + 3000

    print(f"\nTTS complete: {success_count}/{len(narration_lines)} segments synthesized")
    if success_count == 0:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("ERROR: No narration segment was synthesized.", file=sys.stderr)
        sys.exit(1)

    # Concatenate all segments
    print("Concatenating segments with FFmpeg...")
    if concat_wavs(temp_dir, args.output, args.sample_rate):
        output_size = os.path.getsize(args.output)
        duration_ms = get_audio_duration(args.output)
        print(f"Narration saved: {args.output}")
        print(f"   Duration: {duration_ms/1000:.1f}s, Size: {output_size/1024:.0f}KB")
    else:
        print("ERROR: Failed to concatenate narration", file=sys.stderr)
        sys.exit(1)

    # Cleanup temp
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

    # ── Generate timing-accurate subtitles matched to narration audio ──
    if args.output_subs:
        print()
        print("-" * 50)
        print("NARRATION SUBTITLES")
        print("-" * 50)
        srt_entries = generate_narration_srt(segment_timings, args.offset)
        if srt_entries:
            write_srt(srt_entries, args.output_subs)
            print(f"  Subs saved: {args.output_subs} ({len(srt_entries)} entries)")
            print(f"  Language: {args.output_subs_lang}")
            print(f"  Tip: Burn narration subs over video to show spoken text on screen:")
            print(f'    ffmpeg -i video.mp4 -vf "subtitles={args.output_subs}:force_style=\'FontName=Noto Sans TC,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=50,BorderStyle=1\'" -c:v libx264 -crf 23 -c:a copy output.mp4')
        else:
            print("  WARNING: No subtitle entries generated", file=sys.stderr)

    # Print mixing guide
    print()
    print("-" * 50)
    print("MIXING GUIDE")
    print("-" * 50)
    print(f"Edge-TTS voice: {voice}")
    print(f"ffmpeg -i input.mp4 -i {args.output} \\")
    print(f'    -filter_complex "')
    print(f'     [1:a]adelay=0|0[narration];')
    print(f'     [0:a][narration]sidechaincompress=level_in=1:threshold=0.015:ratio=10:attack=100:release=500[ducked];')
    print(f'     [ducked][narration]amix=inputs=2:duration=first:weights=1 1[aout]" \\')
    print(f'    -map 0:v -map "[aout]" -c:v copy -c:a aac output.mp4')

    if args.lang.startswith("zh"):
        print()
        print("  繁體中文發音人: ", voice)
    print()
    print(f"  Tip: Use --offset {args.offset}ms to sync narration with video start")
    print(f"  Tip: For per-segment analysis, reduce --offset to 500ms")


if __name__ == '__main__':
    main()
