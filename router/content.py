"""
API Router for Content Generation Agent.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent.content.graph import build_content_graph
from core.deps import get_current_user
from crud import (
    get_candidate_profile_by_user_id,
    get_job_posting_by_id,
    get_score_by_job_id,
    get_content_by_job_and_profile,
)
from database import get_db
from models import User
from schemas import (
    ContentGenerationRequest,
    GeneratedContentResponse,
)

router = APIRouter(prefix="/content", tags=["content"])


@router.post("/generate", response_model=GeneratedContentResponse, status_code=status.HTTP_201_CREATED)
async def generate_content_endpoint(
    request: ContentGenerationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates personalized job application content (cover letter, email, or recruiter message)
    for a job where score >= 70.
    """
    # 1. Resolve candidate profile for authenticated user
    candidate = await get_candidate_profile_by_user_id(db, current_user.id)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found",
        )

    # 2. Resolve job posting
    job = await get_job_posting_by_id(db, request.job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # 3. Resolve existing score
    score_row = await get_score_by_job_id(db, request.job_id)
    if score_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No score found for this job. Run agent scoring first.",
        )

    # 4. Score threshold check (score >= 70)
    if score_row.score < 70:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Score ({score_row.score}) is below required threshold of 70 for content generation.",
        )

    # 5. Run LangGraph Content Generation workflow
    graph = build_content_graph(db)

    try:
        initial_state = {
            "candidate_profile_id": candidate.id,
            "candidate_name": current_user.name,
            "candidate_skills": candidate.skills or [],
            "job_id": job.job_id,
            "job_title": job.title,
            "company_name": job.company_name,
            "job_description": job.description,
            "required_skills": job.required_skills or [],
            "score": score_row.score,
            "matched_skills": score_row.matched_skills or [],
            "missing_skills": score_row.missing_skills or [],
            "content_type": request.content_type.value,
            "prompt_context": "",
            "generated_content": "",
            "validation_passed": False,
            "persisted_id": None,
        }

        result = await graph.ainvoke(initial_state)

        if not result.get("validation_passed") or not result.get("persisted_id"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate valid content.",
            )

        # Retrieve newly generated content record
        history = await get_content_by_job_and_profile(
            db,
            job_id=job.job_id,
            candidate_profile_id=candidate.id,
            content_type=request.content_type.value,
        )

        if not history:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Content generated but failed to retrieve persisted record.",
            )

        return history[0]

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get("/{job_id}", response_model=list[GeneratedContentResponse])
async def get_generated_content_history(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns previously generated content for a specific job for the authenticated candidate.
    """
    candidate = await get_candidate_profile_by_user_id(db, current_user.id)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found",
        )

    records = await get_content_by_job_and_profile(
        db,
        job_id=job_id,
        candidate_profile_id=candidate.id,
    )
    return records
