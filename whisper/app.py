from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

LOGGER = logging.getLogger("indygestion-whisper")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
MODELS_DIR = os.getenv("HF_HOME", "/models")

app = FastAPI(title="Indygestion Whisper Service", version="0.1.0")

whisper_model = None
embed_model = None


class TranscribeRequest(BaseModel):
    file_path: str = Field(..., description="Path to media file available on shared volume")
    language: str | None = Field(default=None, description="Optional language hint")


class EmbedRequest(BaseModel):
    text: str = Field(..., min_length=1)


@app.on_event("startup")
def startup() -> None:
    global whisper_model, embed_model

    try:
        from faster_whisper import WhisperModel
        from sentence_transformers import SentenceTransformer

        Path(MODELS_DIR).mkdir(parents=True, exist_ok=True)
        LOGGER.info("Loading Whisper model '%s' on %s", WHISPER_MODEL_NAME, WHISPER_DEVICE)
        whisper_model = WhisperModel(
            WHISPER_MODEL_NAME,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
            download_root=MODELS_DIR,
        )

        LOGGER.info("Loading embedding model '%s'", EMBED_MODEL_NAME)
        embed_model = SentenceTransformer(EMBED_MODEL_NAME, cache_folder=MODELS_DIR)
        LOGGER.info("Model preload complete")
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Failed to preload models: %s", exc)
        whisper_model = None
        embed_model = None


@app.get("/health")
def health() -> dict[str, Any]:
    ready = whisper_model is not None and embed_model is not None
    return {
        "ok": ready,
        "whisper_loaded": whisper_model is not None,
        "embed_loaded": embed_model is not None,
        "whisper_model": WHISPER_MODEL_NAME,
        "embed_model": EMBED_MODEL_NAME,
    }


@app.get("/models")
def models() -> dict[str, Any]:
    return {
        "whisper": {
            "configured": WHISPER_MODEL_NAME,
            "loaded": whisper_model is not None,
            "supported_common": ["tiny", "base", "small", "medium", "large-v3"],
        },
        "embedding": {
            "configured": EMBED_MODEL_NAME,
            "loaded": embed_model is not None,
            "dimensions": 384,
        },
    }


@app.post("/transcribe")
def transcribe(req: TranscribeRequest) -> dict[str, Any]:
    if whisper_model is None:
        raise HTTPException(status_code=503, detail="Whisper model not loaded")

    media_path = Path(req.file_path)
    if not media_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {media_path}")

    try:
        LOGGER.info("Transcribing file: %s", media_path)
        segments_iter, info = whisper_model.transcribe(
            str(media_path),
            beam_size=5,
            vad_filter=True,
            language=req.language,
        )

        segments = []
        full_text_parts = []
        for segment in segments_iter:
            seg_text = segment.text.strip()
            segments.append({"start": segment.start, "end": segment.end, "text": seg_text})
            if seg_text:
                full_text_parts.append(seg_text)

        return {
            "segments": segments,
            "full_text": " ".join(full_text_parts).strip(),
            "language": getattr(info, "language", None) or req.language or "unknown",
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Transcription failed for %s: %s", media_path, exc)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc


@app.post("/embed")
def embed(req: EmbedRequest) -> dict[str, Any]:
    if embed_model is None:
        raise HTTPException(status_code=503, detail="Embedding model not loaded")

    try:
        vec = embed_model.encode(req.text, normalize_embeddings=True)
        embedding = vec.tolist() if hasattr(vec, "tolist") else list(vec)
        if len(embedding) != 384:
            raise ValueError(f"Expected 384 dims, got {len(embedding)}")
        return {"embedding": embedding, "model": EMBED_MODEL_NAME}
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Embedding failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Embedding failed: {exc}") from exc
