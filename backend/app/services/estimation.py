from app.services.ffprobe import probe_video

PRESET_RATIOS = {
    "h265_crf18": 0.30,
    "h265_crf22": 0.18,
    "dnxhr_hq": 0.55,
}


def estimate_archive_sizes(path: str, input_size_bytes: int) -> dict:
    metadata = probe_video(path)
    estimates = {}
    for preset, ratio in PRESET_RATIOS.items():
        out_size = int(input_size_bytes * ratio)
        estimates[preset] = {
            "estimated_size_bytes": out_size,
            "saved_bytes": max(input_size_bytes - out_size, 0),
            "saved_percent": round((1 - ratio) * 100, 2),
        }
    return {"metadata": metadata, "estimates": estimates}
