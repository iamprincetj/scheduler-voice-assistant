import logging
import math
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager

from sqlmodel import Session, select
from src.calendar_backend import DBCalendarBackend, LocalJSONCalendar, QuotaEnforcingCalendar, QuotaExceededError
from src.config.base import init_db, get_session
from src.nlu_extractor import IntentExtractor
from src.services.base import hash_password, verify_password, create_access_token, decode_access_token

from src.schemas import ScheduleResponse, TranscriptionResponse, UserLogin, UserRegister, TokenResponse
from src.models.base import User
from src.exceptions.base import GlobalError, global_error_handler

from src.stt_engine import WhisperSTT
from ui.app import start_schedule


logger = logging.getLogger("stt_api")
bearer_scheme = HTTPBearer()

# Load the model ONCE at startup, not per-request.
# Whisper model loading is expensive (reads weights into memory/GPU) -
# doing this insode a route handler would reload it on every single call.

# use "base" for a smaller model size or "small" for slightly large model size
_MODEL_SIZE = "base"
_engine = WhisperSTT(model_size=_MODEL_SIZE)
_extractor = IntentExtractor()
_calendar = QuotaEnforcingCalendar(
    local_backend=LocalJSONCalendar(),
    db_backend=DBCalendarBackend(),
)

# Whisper (via ffmpeg) can actually handle most audio containers regardless
# of extension, but we still validate content-type as a first line of
# defense against someone uploading something that isn't audio at all.
_ALLOWED_CONTENT_TYPES = {
    "audio/wav", "audio/x-wav", "audio/webm", "audio/mpeg",
    "audio/mp4", "audio/ogg", "audio/flac",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Voice Transcription Service",
    description="Internal miscroservice wrapping OpenAI Whisper for speech-to-text.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_exception_handler(GlobalError, global_error_handler)


start_schedule()


@app.get("/")
def home():
    return {"text": "Welcome home!"}


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
async def transcribe_audio(file: UploadFile = File(...)) -> TranscriptionResponse:
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
        raise  # re-raise as-is, don't wrap our own 400s as 500s

    except Exception as exc:
        logger.exception("Transcription fialed")
        raise HTTPException(status_code=500, detail="transcription failed")

    finally:
        tmp_path.unlink(missing_ok=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: Session = Depends(get_session)
) -> User:
    token = credentials.credentials
    email = decode_access_token(token)
    if email is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user = session.exec(select(User).where(User.email == email)).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@app.post("/register", response_model=TokenResponse)
def register(payload: UserRegister, session: Session = Depends(get_session)):
    try:
        existing = session.exec(select(User).where(
            User.email == payload.email)).first()
        if existing:
            raise HTTPException(
                status_code=400, detail="Email already registered")

        hashed_password = hash_password(payload.password)
        user = User(
            email=payload.email,
            hashed_password=hashed_password
        )

        session.add(user)
        session.commit()
        session.refresh(user)

        access_token = create_access_token(payload.email)

        return TokenResponse(
            access_token=access_token
        )
    except Exception as e:
        raise GlobalError(status_code=500, message=f"Internal Error: {e}")


@app.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, session: Session = Depends(get_session)):
    try:
        user = session.exec(select(User).where(
            User.email == payload.email)).first()

        if not user or not verify_password(payload.password, user.hashed_password):
            raise GlobalError(
                status_code=401, message="Invalid email or password")

        access_token = create_access_token(payload.email)

        return TokenResponse(
            access_token=access_token
        )
    except Exception as e:
        raise GlobalError(status_code=500, message=f"Internal Error: {e}")


@app.post(
    "/schedule",
    response_model=ScheduleResponse,
    responses={
        400: {"description": "Invalid or unsupported audio file"},
        401: {"description": "Missing or invalid authentication token"},
        402: {"description": "Local storage quota exceeded; retry with save_to_db=true"},
        500: {"description": "Transcription or booking failed"},
    },
)
async def schedule_event(
    file: UploadFile = File(...),
    save_to_db: bool = False,
    user: User = Depends(get_current_user)
) -> ScheduleResponse:
    """
    Full voice-to-booking flow, scoped to the authenticated user:
    audio -> transcript -> extracted intent -> booked event.

    The first LOCAL_QUOTA events for a user are stored locally for free.
    Beyond that, save_to_db=true must be passed explicitly, or this
    returns 402 with an explanation.
    """

    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise GlobalError(
            400, f"Unsupported content type: {file.content_type}")

    suffix = Path(file.filename or "").suffix or ".wav"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        contents = await file.read()
        tmp.write(contents)

    try:
        transcript = _engine.transcribe(str(tmp_path))
        intent = _extractor.extract(transcript)

        try:
            event = _calendar.book_event(
                intent, user_id=user.id, save_to_db=save_to_db)
        except QuotaExceededError as exc:
            raise GlobalError(402, str(exc))

        return ScheduleResponse(
            transcript=transcript,
            person=intent.person,
            when=intent.parsed_datetime,
            storage=event['storage'],
            event_id=event['id']
        )

    except HTTPException:
        raise

    except Exception:
        logger.exception("Scheduling failed")
        raise GlobalError(500, "Scheduling failed")

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

    avg_logprobs = [seg.get("avg_logprob")
                    for seg in segments if seg.get("avg_logprob") is not None]

    if not avg_logprobs:
        return None

    mean_logprob = sum(avg_logprobs) / len(avg_logprobs)

    return round(min(max(math.exp(mean_logprob), 0.0), 1.0), 3)
