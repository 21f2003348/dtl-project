from typing import Dict


SUPPORTED_LANGUAGES = {"en": "English", "hi": "Hindi", "kn": "Kannada"}


def transcribe_audio(audio_base64: str, language: str) -> Dict[str, str]:
    """Stub transcription. Replace with Whisper/HF call later."""
    if language not in SUPPORTED_LANGUAGES:
        language = "en"
    return {
        "text": "Stub transcription for demo",
        "language": language,
        "engine": "whisper-stub"
    }
