from typing import Dict, Any, Optional
import json
from pathlib import Path

STORAGE_FILE = Path(__file__).parent.parent / "data" / "student_profiles.json"


def _load_profiles() -> Dict[str, Any]:
    if not STORAGE_FILE.exists():
        return {}
    with STORAGE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_profiles(profiles: Dict[str, Any]) -> None:
    STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with STORAGE_FILE.open("w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)


def save_student_profile(student_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    profiles = _load_profiles()
    profiles[student_id] = profile
    _save_profiles(profiles)
    return profile


def get_student_profile(student_id: str) -> Optional[Dict[str, Any]]:
    profiles = _load_profiles()
    return profiles.get(student_id)
