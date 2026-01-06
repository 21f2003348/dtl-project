from typing import Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.student_profile import save_student_profile, get_student_profile

router = APIRouter()


class StudentOnboardingRequest(BaseModel):
    student_id: str = Field(..., description="Unique student identifier")
    college_name: str
    home_location: str
    budget_preference: str = Field("low", description="low, medium, high")
    preferred_modes: list = Field(["Bus", "Metro"], description="Preferred transport modes")


class StudentProfileResponse(BaseModel):
    student_id: str
    profile: Dict[str, Any]


@router.post("/student/onboard", response_model=StudentProfileResponse)
async def onboard_student(payload: StudentOnboardingRequest):
    profile = {
        "college_name": payload.college_name,
        "home_location": payload.home_location,
        "budget_preference": payload.budget_preference,
        "preferred_modes": payload.preferred_modes
    }
    saved = save_student_profile(payload.student_id, profile)
    return {"student_id": payload.student_id, "profile": saved}


@router.get("/student/profile/{student_id}", response_model=StudentProfileResponse)
async def get_profile(student_id: str):
    profile = get_student_profile(student_id)
    if not profile:
        return {"student_id": student_id, "profile": {}}
    return {"student_id": student_id, "profile": profile}
