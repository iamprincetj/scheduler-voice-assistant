from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    """
    Response returned after successfully transcriing an audio file.
    """

    text: str = Field(...,
                      description="The transcribed text, whitespace-trimmed")
    confidence: float | None = Field(
        None,
        description=(
            "Rough 0-1 confidence heuristic derived from Whisper's segment "
            "log-probabilities. Not a calibrated probability - treat as a "
            "relative signal only (e.g. for deciding whether to force a )"
            "confirmation step), not an acuuracy guarantee."
        ),
    )
    model_size: str = Field(...,
                            description="Which Whisper model size produced this result")


class ErrorResponse(BaseModel):
    """Standard error shape returned on failure."""
    detail: str


class UserRegister(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ScheduleResponse(BaseModel):
    """Response returned after successfully transcribing audio and booking an event."""

    transcript: str = Field(..., description="The transcribed text")
    person: str | None = Field(
        None, description="Extracted person's name, if detected")
    when: str | None = Field(
        None, description="Extracted ISO datetime, if detected")
    storage: str = Field(...,
                         description="Where this event was stored: 'local' or 'database'")
    event_id: str = Field(..., description="Unique ID of the booked event")
