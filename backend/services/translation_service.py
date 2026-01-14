"""
Translation Service using Sarvam AI API.
Supports translation between English, Hindi, and Kannada.
"""
import os
import requests
from typing import Dict, List, Optional


# Sarvam AI API configuration
SARVAM_API_URL = "https://api.sarvam.ai/translate"

# Supported language codes (ISO format for Sarvam)
LANGUAGE_CODES = {
    "en": "en-IN",
    "hi": "hi-IN",
    "kn": "kn-IN",
    "en-IN": "en-IN",
    "hi-IN": "hi-IN",
    "kn-IN": "kn-IN"
}

LANGUAGE_NAMES = {
    "en": "English",
    "en-IN": "English",
    "hi": "Hindi",
    "hi-IN": "Hindi",
    "kn": "Kannada",
    "kn-IN": "Kannada"
}


def get_sarvam_api_key() -> Optional[str]:
    """Get Sarvam AI API key from environment."""
    return os.getenv("SARVAM_API_KEY") or os.getenv("SARVAM_API_SUBSCRIPTION_KEY")


def normalize_language_code(code: str) -> str:
    """Normalize language code to Sarvam format (e.g., 'en' -> 'en-IN')."""
    return LANGUAGE_CODES.get(code, code)


def translate_text(
    text: str,
    source_language: str,
    target_language: str
) -> Dict[str, str]:
    """
    Translate text using Sarvam AI API.
    
    Args:
        text: Text to translate
        source_language: Source language code (en, hi, kn)
        target_language: Target language code (en, hi, kn)
    
    Returns:
        Dict with translated_text, source_language, target_language
    """
    if not text or not text.strip():
        return {
            "translated_text": "",
            "source_language": source_language,
            "target_language": target_language,
            "engine": "sarvam-translate"
        }
    
    # Normalize language codes
    src_code = normalize_language_code(source_language)
    tgt_code = normalize_language_code(target_language)
    
    # If same language, return as-is
    if src_code == tgt_code:
        return {
            "translated_text": text,
            "source_language": source_language,
            "target_language": target_language,
            "engine": "passthrough"
        }
    
    api_key = get_sarvam_api_key()
    
    if not api_key:
        print("[TRANSLATION] No SARVAM_API_KEY found, using fallback")
        return _fallback_translation(text, source_language, target_language)
    
    try:
        headers = {
            "api-subscription-key": api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "input": text,
            "source_language_code": src_code,
            "target_language_code": tgt_code,
            "model": "sarvam-translate:v1"
        }
        
        response = requests.post(
            SARVAM_API_URL,
            headers=headers,
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            translated = result.get("translated_text", text)
            
            return {
                "translated_text": translated,
                "source_language": source_language,
                "target_language": target_language,
                "engine": "sarvam-translate:v1"
            }
        else:
            print(f"[TRANSLATION] API error: {response.status_code} - {response.text}")
            return _fallback_translation(text, source_language, target_language, error=response.text)
            
    except requests.RequestException as e:
        print(f"[TRANSLATION] Request error: {e}")
        return _fallback_translation(text, source_language, target_language, error=str(e))
    except Exception as e:
        print(f"[TRANSLATION] Unexpected error: {e}")
        return _fallback_translation(text, source_language, target_language, error=str(e))


def _fallback_translation(
    text: str,
    source_language: str,
    target_language: str,
    error: Optional[str] = None
) -> Dict[str, str]:
    """Fallback when API is unavailable - returns original text."""
    result = {
        "translated_text": text,  # Return original text as fallback
        "source_language": source_language,
        "target_language": target_language,
        "engine": "fallback"
    }
    if error:
        result["error"] = error
    return result


def translate_batch(
    texts: List[str],
    source_language: str,
    target_language: str
) -> List[Dict[str, str]]:
    """
    Translate multiple texts.
    
    Args:
        texts: List of texts to translate
        source_language: Source language code
        target_language: Target language code
    
    Returns:
        List of translation results
    """
    results = []
    for text in texts:
        result = translate_text(text, source_language, target_language)
        results.append(result)
    return results


def get_supported_languages() -> Dict[str, str]:
    """Get list of supported languages."""
    return {
        "en": "English",
        "hi": "Hindi",
        "kn": "Kannada"
    }
