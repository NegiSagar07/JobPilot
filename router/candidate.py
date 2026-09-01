from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from crud import create_candidate_profile, get_candidate_profile_by_user_id
from database import get_db
from schemas import CandidateProfile, CandidateProfileCreate
from core.deps import get_current_user
from models import User


router = APIRouter(
    prefix="/candidate_profiles",
    tags=["candidate_profiles"],
)


@router.post("/", response_model=CandidateProfile)
async def create_candidate_profile_endpoint(
    candidate_profile: CandidateProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    existing_profile = await get_candidate_profile_by_user_id(
        db,
        current_user.id,
    )

    if existing_profile:
        raise HTTPException(
            status_code=409,
            detail="Candidate profile already exists",
        )
    return await create_candidate_profile(
        db,
        candidate_profile,
        current_user.id,
    )