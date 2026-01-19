"""
Translation Routes - API endpoints for text translation.
"""
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.translation_service import (
    translate_text,
    translate_batch,
    get_supported_languages
)


router = APIRouter(prefix="/api", tags=["translation"])


class TranslateRequest(BaseModel):
    """Request model for text translation."""
    text: str = Field(..., description="Text to translate", max_length=2000)
    source_language: Literal["en", "hi", "kn", "en-IN", "hi-IN", "kn-IN"] = Field(
        ..., description="Source language code"
    )
    target_language: Literal["en", "hi", "kn", "en-IN", "hi-IN", "kn-IN"] = Field(
        ..., description="Target language code"
    )


class TranslateResponse(BaseModel):
    """Response model for translation."""
    status: str
    translated_text: str
    source_language: str
    target_language: str
    engine: str
    error: Optional[str] = None


class BatchTranslateRequest(BaseModel):
    """Request model for batch translation."""
    texts: List[str] = Field(..., description="List of texts to translate", max_items=50)
    source_language: Literal["en", "hi", "kn", "en-IN", "hi-IN", "kn-IN"] = Field(
        ..., description="Source language code"
    )
    target_language: Literal["en", "hi", "kn", "en-IN", "hi-IN", "kn-IN"] = Field(
        ..., description="Target language code"
    )


class BatchTranslateResponse(BaseModel):
    """Response model for batch translation."""
    status: str
    translations: List[TranslateResponse]


@router.post("/translate", response_model=TranslateResponse)
async def translate_text_endpoint(payload: TranslateRequest) -> TranslateResponse:
    """
    Translate text between supported languages.
    
    Supports translation between English, Hindi, and Kannada.
    Maximum 2000 characters per request.
    """
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")
    
    result = translate_text(
        payload.text,
        payload.source_language,
        payload.target_language
    )
    
    return TranslateResponse(
        status="success" if not result.get("error") else "error",
        translated_text=result.get("translated_text", payload.text),
        source_language=result.get("source_language", payload.source_language),
        target_language=result.get("target_language", payload.target_language),
        engine=result.get("engine", "unknown"),
        error=result.get("error")
    )


@router.post("/translate/batch", response_model=BatchTranslateResponse)
async def translate_batch_endpoint(payload: BatchTranslateRequest) -> BatchTranslateResponse:
    """
    Translate multiple texts in a single request.
    
    Maximum 50 texts per request.
    """
    if not payload.texts:
        raise HTTPException(status_code=400, detail="At least one text is required")
    
    results = translate_batch(
        payload.texts,
        payload.source_language,
        payload.target_language
    )
    
    translations = [
        TranslateResponse(
            status="success" if not r.get("error") else "error",
            translated_text=r.get("translated_text", ""),
            source_language=r.get("source_language", payload.source_language),
            target_language=r.get("target_language", payload.target_language),
            engine=r.get("engine", "unknown"),
            error=r.get("error")
        )
        for r in results
    ]
    
    return BatchTranslateResponse(
        status="success",
        translations=translations
    )


@router.get("/translate/languages")
async def get_languages():
    """Get list of supported languages for translation."""
    return {
        "status": "success",
        "languages": get_supported_languages()
    }
