from __future__ import annotations

import json
import math
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path


def check_qsv_available() -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False

    result = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True)
    if result.returncode != 0:
        return False

    return "h264_qsv" in result.stdout and "hevc_qsv" in result.stdout


def build_proxy_command(input_path: str, output_path: str, use_qsv: bool = True) -> list[str]:
    scale_filter = "scale='if(gt(iw,1920),1920,iw)':'if(gt(ih,1080),1080,ih)':force_original_aspect_ratio=decrease"

    common = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-vf",
        scale_filter,
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        "-pix_fmt",
        "yuv420p",
    ]

    if use_qsv:
        return [
            *common,
            "-c:v",
            "h264_qsv",
            "-b:v",
            "8M",
            "-maxrate",
            "10M",
            "-bufsize",
            "16M",
            "-global_quality",
            "23",
            str(output_path),
        ]

    return [
        *common,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "22",
        "-b:v",
        "8M",
        "-maxrate",
        "10M",
        "-bufsize",
        "16M",
        str(output_path),
    ]


def build_archive_command(
    input_path: str,
    output_path: str,
    codec: str,
    crf: int,
    use_qsv: bool = True,
) -> list[str]:
    base = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-map",
        "0",
    ]

    normalized = codec.lower()

    if normalized in {"h265", "hevc", "h265_qsv", "hevc_qsv"}:
        if use_qsv:
            return [
                *base,
                "-c:v",
                "hevc_qsv",
                "-global_quality",
                str(crf),
                "-look_ahead",
                "1",
                "-c:a",
                "copy",
                str(output_path),
            ]
        return [
            *base,
            "-c:v",
            "libx265",
            "-crf",
            str(crf),
            "-preset",
            "slow",
            "-c:a",
            "copy",
            str(output_path),
        ]

    if normalized in {"dnxhd", "dnxhr"}:
        # DNxHR HQ-ish default, variable source support
        return [
            *base,
            "-c:v",
            "dnxhd",
            "-profile:v",
            "dnxhr_hq",
            "-pix_fmt",
            "yuv422p",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]

    raise ValueError(f"Unsupported archive codec: {codec}")


def probe_file(input_path: str) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(input_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {input_path}: {result.stderr.strip()}")

    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    format_info = data.get("format", {})
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})

    fps_raw = video_stream.get("r_frame_rate") or "0/1"
    try:
        fps = float(Fraction(fps_raw))
    except Exception:
        fps = 0.0

    duration = float(video_stream.get("duration") or format_info.get("duration") or 0)
    bitrate = int(video_stream.get("bit_rate") or format_info.get("bit_rate") or 0)

    frame_count = video_stream.get("nb_frames")
    if frame_count is None and fps and duration:
        frame_count = int(round(fps * duration))

    return {
        "width": int(video_stream.get("width") or 0),
        "height": int(video_stream.get("height") or 0),
        "codec": video_stream.get("codec_name"),
        "duration": duration,
        "bitrate": bitrate,
        "fps": fps,
        "frame_count": int(frame_count or 0),
    }


def estimate_output_size(input_info: dict, codec: str, crf: int) -> int:
    duration = float(input_info.get("duration") or 0)
    source_bitrate = int(input_info.get("bitrate") or 0)

    if duration <= 0:
        return 0

    normalized = codec.lower()
    if normalized in {"h265", "hevc", "h265_qsv", "hevc_qsv"}:
        ratio = 0.30 if crf <= 18 else 0.20 if crf <= 22 else 0.14
    elif normalized in {"dnxhd", "dnxhr"}:
        ratio = 0.55
    else:
        ratio = 0.35

    if source_bitrate <= 0:
        width = int(input_info.get("width") or 1920)
        height = int(input_info.get("height") or 1080)
        pixels = width * height
        source_bitrate = int(max(8_000_000, pixels * 0.18))

    estimated_bits = source_bitrate * duration * ratio
    return int(math.ceil(estimated_bits / 8))
