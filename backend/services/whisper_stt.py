"""
Whisper Speech-to-Text Service using Hugging Face Router API.
Uses openai/whisper-large-v3 model for transcription.
"""
import os
import base64
import requests
from typing import Dict, Optional


SUPPORTED_LANGUAGES = {"en": "English", "hi": "Hindi", "kn": "Kannada"}

# Hugging Face Router API configuration (updated from deprecated api-inference.huggingface.co)
HF_API_URL = "https://router.huggingface.co/hf-inference/models/openai/whisper-large-v3"

# Language code mapping for Whisper
LANGUAGE_CODES = {
    "en": "english",
    "hi": "hindi", 
    "kn": "kannada"
}


def get_hf_token() -> Optional[str]:
    """Get Hugging Face API token from environment."""
    return os.getenv("HF_API_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")


def transcribe_audio(audio_base64: str, language: str) -> Dict[str, str]:
    """
    Transcribe audio using Hugging Face Whisper Router API.
    
    Args:
        audio_base64: Base64 encoded audio data
        language: Language code (en, hi, kn)
    
    Returns:
        Dict with text, language, and engine info
    """
    if language not in SUPPORTED_LANGUAGES:
        language = "en"
    
    if not audio_base64 or audio_base64.strip() == "":
        return _fallback_transcription(language, error="Empty audio input")
    
    hf_token = get_hf_token()
    
    if not hf_token:
        print("[WHISPER] No HF_API_TOKEN found, using fallback")
        return _fallback_transcription(language, error="No API token configured")
    
    try:
        # Decode base64 audio
        audio_bytes = base64.b64decode(audio_base64)
        
        # Get the full language name for Whisper
        whisper_lang = LANGUAGE_CODES.get(language, "english")
        
        headers = {
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "audio/wav"
        }
        
        # Add parameters for better Indian accent recognition
        # The API accepts parameters via query string or JSON
        
        # Comprehensive Indian context prompt for better accent recognition
        # Includes: place names, transport terms, common phrases with Indian pronunciation
        indian_context_prompt = (
            "Indian English accent. Travel query in India. "
            # Bengaluru places (with common pronunciation variations)
            "Bengaluru places: Majestic, Hebbal, Koramangala, Indiranagar, Whitefield, "
            "Electronic City, Jayanagar, Banashankari, JP Nagar, BTM Layout, "
            "Yeshwanthpur, Yelahanka, Kengeri, RVCE, Silk Board, Marathahalli, "
            "MG Road, Brigade Road, Shivajinagar, Vijayanagar. "
            # Mumbai places
            "Mumbai places: Dadar, Andheri, Bandra, Kurla, Thane, Borivali, "
            "Churchgate, CST, Malad, Goregaon, Worli, Lower Parel. "
            # Transport terms
            "Transport: BMTC bus, Namma Metro, auto rickshaw, Ola cab, Uber, Rapido, "
            "bus stop, metro station, railway station. "
            # Common phrases
            "Common phrases: I want to go, how to reach, best route, cheapest way, "
            "fastest route, from here to, take me to."
        )
        
        # Note: HF Inference API for Whisper doesn't accept language/prompt as query params
        # The model auto-detects language. The context prompt helps with vocabulary.
        # We log the intended language for debugging purposes.
        
        # Send to Hugging Face Router API
        print(f"[WHISPER] Sending {len(audio_bytes)} bytes for {whisper_lang} transcription...")
        
        # Send binary audio directly (HF Inference API format)
        response = requests.post(
            HF_API_URL,
            headers=headers,
            data=audio_bytes,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            transcribed_text = result.get("text", "").strip()
            print(f"[WHISPER] Transcribed: '{transcribed_text}'")
            
            return {
                "text": transcribed_text,
                "language": language,
                "engine": "whisper-large-v3"
            }
        elif response.status_code == 503:
            # Model is loading
            print(f"[WHISPER] Model loading: {response.json()}")
            return {
                "text": "",
                "language": language,
                "engine": "whisper-large-v3",
                "error": "Model is loading, please try again in a few seconds"
            }
        else:
            print(f"[WHISPER] API error: {response.status_code} - {response.text}")
            return _fallback_transcription(language, error=f"API error: {response.status_code}")
            
    except base64.binascii.Error as e:
        print(f"[WHISPER] Base64 decode error: {e}")
        return _fallback_transcription(language, error="Invalid audio data format")
    except requests.RequestException as e:
        print(f"[WHISPER] Request error: {e}")
        return _fallback_transcription(language, error=str(e))
    except Exception as e:
        print(f"[WHISPER] Unexpected error: {e}")
        return _fallback_transcription(language, error=str(e))


def _fallback_transcription(language: str, error: Optional[str] = None) -> Dict[str, str]:
    """Fallback when API is unavailable."""
    result = {
        "text": "",
        "language": language,
        "engine": "whisper-fallback"
    }
    if error:
        result["error"] = error
    return result
