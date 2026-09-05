import logging
import math
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from src.schemas import TranscriptionResponse
from src.stt_engine import WhisperSTT


logger = logging.getLogger("stt_api")

# Load the model ONCE at startup, not per-request.
# Whisper model loading is expensive (reads weights into memory/GPU) - 
# doing this insode a route handler would reload it on every single call.

_MODEL_SIZE = "base" # use "base" for a smaller model size or "small" for slightly large model size
_engine = WhisperSTT(model_size=_MODEL_SIZE)

# Whisper (via ffmpeg) can actually handle most audio containers regardless
# of extension, but we still validate content-type as a first line of
# defense against someone uploading something that isn't audio at all.
_ALLOWED_CONTENT_TYPES = {
    "audio/wav", "audio/x-wav", "audio/webm", "audio/mpeg",
    "audio/mp4", "audio/ogg", "audio/flac",
}


app = FastAPI(
    title="Voice Transcription Service",
    description="Internal miscroservice wrapping OpenAI Whisper for speech-to-text.",
    version="1.0.0"
)

@app.get("/health")
def health_check() -> dict:
    """
    Basic liveness check - confirms the process is up and the model loaded.
    """
    return {"status": "ok", "model_size": _MODEL_SIZE}


@app.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    responses={
        400: {"description": "Invalid or unsupported audio file"},
        500: {
            "description": "Transcription failed"
        },
    }
)
async def transcribe_audio(file: UploadFile= File(...)) -> TranscriptionResponse:
    """
    Accepts an uploaded audio file and returns it transcript.

    Flow:
    1. Validates the upload has a recognizable audio content-type
    2. Write it to a temp file on disk (Whisper's API expects a file path, not raw bytes in memory).
    3. Run it through the already-loaded WhisperSTT engine
    4. Clean up the temp file regardless of success or failure.
    """

    # 1

    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported content type: {file.content_type}"
        )

    suffix = Path(file.filename or "").suffix or ".wav"

    # delete=False because we need the file to still exist on disk when we
    # hand its path to whisper; we delete it ourselves in the `finally` block.

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        contents = await file.read()
        tmp.write(contents)

    try:
        result = _engine._model.transcribe(str(tmp_path))
        text = result["text"].strip()
        confidence = _estimate_confidence(result)

        if not text:
            raise HTTPException(
                status_code=400,
                detail="Transcription produced empty text - audio may be silent or unintelligible."
            )

        return TranscriptionResponse(
            text=text,
            confidence=confidence,
            model_size=_MODEL_SIZE
        )

    except HTTPException:
        raise # re-raise as-is, don't wrap our own 400s as 500s

    except Exception as exc:
        logger.exception("Transcription fialed")
        raise HTTPException(status_code=500, detail="transcription failed")

    finally:
        tmp_path.unlink(missing_ok=True)


def _estimate_confidence(whisper_result: dict) -> float | None:
    """
    Whisper doesn't return a single confidence score — it returns per-segment
    average log-probabilities. This converts those into a rough 0-1 heuristic
    by averaging across segments and exponentiating (log-prob -> probability-like scale).

    This is intentionally simple and documented as a heuristic in the schema —
    resist the temptation to treat it as ground truth.
    """

    segments = whisper_result.get("segments")

    if not segments:
        return None

    avg_logprobs = [seg.get("avg_logprob") for seg in segments if seg.get("avg_logprob") is not None]

    if not avg_logprobs:
        return None

    mean_logprob = sum(avg_logprobs) / len(avg_logprobs)

    return round(min(max(math.exp(mean_logprob), 0.0), 1.0), 3)