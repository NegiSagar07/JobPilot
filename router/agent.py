"""
API Router for Agent Execution Runs.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent.indeed_fetcher import IndeedScraperError
from agent.runner import AgentRunSummary, run_job_search_agent
from core.deps import get_current_user
from crud import get_candidate_profile_by_user_id
from database import get_db
from models import User

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run", response_model=AgentRunSummary)
async def trigger_agent_run(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Triggers an autonomous job search run for the authenticated user's profile.
    """
    candidate_profile = await get_candidate_profile_by_user_id(
        db,
        current_user.id,
    )
    if candidate_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found",
        )

    try:
        summary = await run_job_search_agent(candidate_profile.id, db)
        return summary
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except IndeedScraperError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
