"""
Transcription Routes - API endpoints for speech-to-text.
"""
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.whisper_stt import transcribe_audio, SUPPORTED_LANGUAGES


router = APIRouter(prefix="/api", tags=["transcription"])


class TranscribeRequest(BaseModel):
    """Request model for audio transcription."""
    audio: str = Field(..., description="Base64 encoded audio data")
    language: Literal["en", "hi", "kn"] = Field("en", description="Language code")


class TranscribeResponse(BaseModel):
    """Response model for transcription."""
    status: str
    text: str
    language: str
    engine: str
    error: Optional[str] = None


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio_endpoint(payload: TranscribeRequest) -> TranscribeResponse:
    """
    Transcribe audio to text using Whisper.
    
    Accepts base64-encoded audio data and returns transcribed text.
    Supports English, Hindi, and Kannada.
    """
    if not payload.audio:
        raise HTTPException(status_code=400, detail="Audio data is required")
    
    result = transcribe_audio(payload.audio, payload.language)
    
    return TranscribeResponse(
        status="success" if result.get("text") or not result.get("error") else "error",
        text=result.get("text", ""),
        language=result.get("language", payload.language),
        engine=result.get("engine", "unknown"),
        error=result.get("error")
    )


@router.get("/transcribe/languages")
async def get_supported_languages():
    """Get list of supported languages for transcription."""
    return {
        "status": "success",
        "languages": SUPPORTED_LANGUAGES
    }
