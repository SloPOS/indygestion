import json
import subprocess


def probe_video(path: str) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        path,
    ]
    out = subprocess.check_output(cmd, text=True)
    data = json.loads(out)

    video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    width = video_stream.get("width")
    height = video_stream.get("height")
    r_frame_rate = video_stream.get("r_frame_rate", "0/1")
    num, den = r_frame_rate.split("/")
    fps = float(num) / float(den) if float(den) else 0.0

    return {
        "duration": float(data.get("format", {}).get("duration", 0) or 0),
        "bitrate": int(float(data.get("format", {}).get("bit_rate", 0) or 0)),
        "codec": video_stream.get("codec_name"),
        "resolution": f"{width}x{height}" if width and height else None,
        "fps": fps,
    }
