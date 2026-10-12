from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    """
    Response returned after successfully transcriing an audio file.
    """

    text: str = Field(..., description="The transcribed text, whitespace-trimmed")
    confidence: float | None = Field(
        None,
        description=(
            "Rough 0-1 confidence heuristic derived from Whisper's segment "
            "log-probabilities. Not a calibrated probability - treat as a "
            "relative signal only (e.g. for deciding whether to force a )"
            "confirmation step), not an acuuracy guarantee."
        ),
    )
    model_size: str = Field(..., description="Which Whisper model size produced this result")



class ErrorResponse(BaseModel):
    """Standard error shape returned on failure."""
    detail: str