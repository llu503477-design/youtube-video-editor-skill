#!/usr/bin/env python3
"""thumbnail.py — YouTube Thumbnail Generator.

Creates eye-catching YouTube thumbnails (1280×720) with:
- A background image (or video frame)
- Large bold title text
- Optional subtitle line
- Auto font fallback for CJK characters (Noto Sans TC)
- Configurable colors, gradient overlays, and positioning

Usage:
    # From an image
    python thumbnail.py --bg background.jpg --title "影片標題" --output thumb.jpg

    # From a video frame at 10s
    python thumbnail.py --video input.mp4 --time 10 --title "超強教學" --subtitle "Complete Tutorial" --output thumb.jpg

    # Full customization
    python thumbnail.py --bg bg.jpg --title "重磅消息" --title-size 120 --subtitle "Breaking News" --text-color "#FFFFFF" --glow "#FF4400" --output thumb.jpg
"""

import sys
import os
import re
import subprocess
import argparse
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow", file=sys.stderr)
    sys.exit(1)


# ── Defaults ──
THUMB_W, THUMB_H = 1280, 720  # YouTube standard thumbnail
DEFAULT_TITLE_SIZE = 90
DEFAULT_SUB_SIZE = 45
DEFAULT_TEXT_COLOR = "#FFFFFF"
DEFAULT_GLOW_COLOR = "#FF6600"
DEFAULT_TITLE_POS = (640, 380)  # center, slightly below middle
DEFAULT_SUB_POS = (640, 500)
OVERLAY_ALPHA = 0.35  # dark gradient overlay strength


def extract_video_frame(video_path, time_sec=10, output_path=None):
    """Extract a single frame from video at given time using FFmpeg."""
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(time_sec),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            output_path,
        ], check=True, capture_output=True, timeout=120)
        return output_path
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"ERROR: FFmpeg frame extraction failed: {e}", file=sys.stderr)
        return None


def load_background(bg_path, target_size=(THUMB_W, THUMB_H)):
    """Load and resize background image to target size (cover/crop)."""
    try:
        img = Image.open(bg_path).convert("RGB")
        # Cover crop: resize to fill target, then center crop
        img_ratio = img.width / img.height
        target_ratio = target_size[0] / target_size[1]
        if img_ratio > target_ratio:
            # Image is wider: match height, crop width
            new_h = target_size[1]
            new_w = int(new_h * img_ratio)
        else:
            # Image is taller: match width, crop height
            new_w = target_size[0]
            new_h = int(new_w / img_ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        # Center crop
        left = (new_w - target_size[0]) // 2
        top = (new_h - target_size[1]) // 2
        img = img.crop((left, top, left + target_size[0], top + target_size[1]))
        return img
    except Exception as e:
        print(f"ERROR: Cannot load background image: {e}", file=sys.stderr)
        return None


def apply_gradient_overlay(draw, width, height, alpha=OVERLAY_ALPHA):
    """Apply dark gradient overlay: darker at bottom, lighter at top."""
    for y in range(height):
        # Linear gradient: 0 at top, alpha at bottom
        t = y / height
        current_alpha = int(alpha * t * 255)
        if current_alpha > 0:
            draw.rectangle([0, y, width, y + 1], fill=(0, 0, 0, current_alpha))


def add_glow_text(draw, text, position, font, text_color, glow_color, glow_radius=6):
    """Draw text with outer glow effect by layering multiple passes."""
    x, y = position
    # Use textbbox to center the text
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    cx = x - tw // 2
    cy = y - th // 2

    # Glow layers (wider to narrower)
    for r in range(glow_radius, 0, -1):
        glow_alpha = int(80 * (1 - r / (glow_radius + 1)))
        glow_hex = _alpha_hex(glow_color, glow_alpha)
        draw.text((cx + r, cy + r), text, font=font, fill=glow_hex)
        draw.text((cx - r, cy + r), text, font=font, fill=glow_hex)
        draw.text((cx + r, cy - r), text, font=font, fill=glow_hex)
        draw.text((cx - r, cy - r), text, font=font, fill=glow_hex)
        draw.text((cx + r, cy), text, font=font, fill=glow_hex)
        draw.text((cx - r, cy), text, font=font, fill=glow_hex)
        draw.text((cx, cy + r), text, font=font, fill=glow_hex)
        draw.text((cx, cy - r), text, font=font, fill=glow_hex)

    # Main text (solid white)
    draw.text((cx, cy), text, font=font, fill=text_color)


def _alpha_hex(color, alpha):
    """Convert color hex + alpha int to Pillow RGBA tuple."""
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    return (r, g, b, alpha)


def find_font(preferred_size):
    """Find best available font. Prefer Noto Sans variants for CJK support."""
    # Try common font paths (Windows + common paths)
    candidates = [
        # Noto Sans TC (priority — open-source, CJK support)
        ("C:/Windows/Fonts/NotoSansTC-Regular.otf", "C:/Windows/Fonts/NotoSansTC-Bold.otf"),
        # Fallback CJK fonts
        ("C:/Windows/Fonts/msjh.ttc", None),          # Microsoft JhengHei
        ("C:/Windows/Fonts/msyh.ttc", None),           # Microsoft YaHei
        ("C:/Windows/Fonts/msgothic.ttc", None),       # MS Gothic
        # Sans-serif fallback
        ("C:/Windows/Fonts/arial.ttf", None),
        ("C:/Windows/Fonts/arialbd.ttf", None),
        ("C:/Windows/Fonts/segoeui.ttf", None),
        ("C:/Windows/Fonts/segoeuib.ttf", None),
    ]

    # Prefer the bold face when a pair is available, then use the regular face.
    for regular_path, bold_path in candidates:
        for font_path in (bold_path, regular_path):
            if not font_path or not os.path.exists(font_path):
                continue
            try:
                return ImageFont.truetype(font_path, preferred_size)
            except Exception:
                continue

    # Ultimate fallback: default font
    print("  INFO: Using default Pillow font (no CJK support - text may show as boxes)",
          file=sys.stderr)
    return ImageFont.load_default()


def create_thumbnail(bg_path, title, subtitle=None, output_path="thumbnail.jpg",
                     title_size=DEFAULT_TITLE_SIZE, sub_size=DEFAULT_SUB_SIZE,
                     text_color=DEFAULT_TEXT_COLOR, glow_color=DEFAULT_GLOW_COLOR,
                     title_pos=None, sub_pos=None, force=False):
    """Create a YouTube thumbnail with title text overlay.

    Args:
        bg_path: Background image path (or extracted frame)
        title: Main title text (large, eye-catching)
        subtitle: Optional subtitle/secondary text
        output_path: Output JPEG path
        title_size: Font size for title (default: 90)
        sub_size: Font size for subtitle (default: 45)
        text_color: Text color hex (default: #FFFFFF)
        glow_color: Glow/outline color hex (default: #FF6600)
        title_pos: (x, y) for title center, or None for default
        sub_pos: (x, y) for subtitle center, or None for default
        force: Overwrite output_path when True
    """
    if os.path.exists(output_path) and not force:
        raise FileExistsError(
            f"Output already exists: {output_path}. Use force=True or --force to overwrite it."
        )
    # Load background (create gradient fallback if None or invalid)
    bg = load_background(bg_path) if bg_path else None
    if bg is None:
        # Create gradient fallback background
        bg = Image.new("RGB", (THUMB_W, THUMB_H), (20, 20, 40))
        draw = ImageDraw.Draw(bg)
        for y in range(THUMB_H):
            t = y / THUMB_H
            r = int(20 + 60 * t)
            g = int(20 + 40 * t)
            b = int(40 + 80 * t)
            draw.line([(0, y), (THUMB_W, y)], fill=(r, g, b))

    # Enable alpha for overlay
    bg = bg.convert("RGBA")
    overlay = Image.new("RGBA", (THUMB_W, THUMB_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Apply gradient overlay
    apply_gradient_overlay(draw, THUMB_W, THUMB_H)

    # Composite overlay
    bg.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(bg)

    # Resolve fonts
    title_font = find_font(title_size)
    sub_font = find_font(sub_size) if subtitle else None

    # Default positions (centered)
    if title_pos is None:
        title_pos = DEFAULT_TITLE_POS
    if sub_pos is None:
        sub_pos = DEFAULT_SUB_POS

    # Draw subtitle first (behind title glow)
    if subtitle and sub_font:
        add_glow_text(draw, subtitle, sub_pos, sub_font, text_color, glow_color, glow_radius=4)

    # Draw title
    add_glow_text(draw, title, title_pos, title_font, text_color, glow_color, glow_radius=8)

    # Save as JPEG (max quality)
    bg = bg.convert("RGB")
    bg.save(output_path, "JPEG", quality=95)
    filesize = os.path.getsize(output_path)
    print(f"[OK] Thumbnail saved: {output_path} ({THUMB_W}x{THUMB_H}, {filesize/1024:.0f}KB)")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Thumbnail Generator - eye-catching title text overlay"
    )
    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--bg", help="Background image path")
    input_group.add_argument("--video", help="Video file (extract frame as background)")

    parser.add_argument("--time", type=int, default=10,
                        help="Frame time in seconds for --video (default: 10)")
    parser.add_argument("--output", "-o", default="thumbnail.jpg", help="Output JPEG")
    parser.add_argument("--title", required=True, help="Main title text")
    parser.add_argument("--subtitle", help="Subtitle/secondary text (optional)")
    parser.add_argument("--title-size", type=int, default=DEFAULT_TITLE_SIZE,
                        help=f"Title font size (default: {DEFAULT_TITLE_SIZE})")
    parser.add_argument("--sub-size", type=int, default=DEFAULT_SUB_SIZE,
                        help=f"Subtitle font size (default: {DEFAULT_SUB_SIZE})")
    parser.add_argument("--text-color", default=DEFAULT_TEXT_COLOR,
                        help=f"Text color hex (default: {DEFAULT_TEXT_COLOR})")
    parser.add_argument("--glow", default=DEFAULT_GLOW_COLOR,
                        help=f"Glow/outline color hex (default: {DEFAULT_GLOW_COLOR})")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output file")

    args = parser.parse_args()
    if args.title_size <= 0 or args.sub_size <= 0:
        parser.error("Font sizes must be greater than zero")
    if args.time < 0:
        parser.error("--time must be zero or greater")
    if os.path.exists(args.output) and not args.force:
        parser.error(f"Output already exists: {args.output}. Use --force to overwrite it.")

    # Resolve background source
    if args.video:
        print(f"Extracting frame at {args.time}s from: {args.video}")
        frame_path = extract_video_frame(args.video, args.time)
        if frame_path is None:
            sys.exit(1)
        bg_path = frame_path
        cleanup_frame = True
    else:
        bg_path = args.bg
        cleanup_frame = False
        if not os.path.exists(bg_path) or not bg_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp')):
            print(f"  WARNING: Background not found or invalid format: {bg_path}", file=sys.stderr)
            print("  Creating gradient fallback background...", file=sys.stderr)
            bg_path = None

    # Generate thumbnail
    print(f"Title: {args.title}")
    if args.subtitle:
        print(f"Subtitle: {args.subtitle}")
    print(f"Title size: {args.title_size}px")

    try:
        create_thumbnail(
            bg_path=bg_path,
            title=args.title,
            subtitle=args.subtitle,
            output_path=args.output,
            title_size=args.title_size,
            sub_size=args.sub_size,
            text_color=args.text_color,
            glow_color=args.glow,
            force=args.force,
        )
    finally:
        # Cleanup extracted frame.
        if cleanup_frame and os.path.exists(bg_path):
            try:
                os.remove(bg_path)
            except OSError:
                pass


if __name__ == '__main__':
    main()
