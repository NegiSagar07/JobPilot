from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from agent.scoring_runner import should_trigger_content_generator
from core.deps import get_current_user
from crud import (
    create_job_posting,
    get_all_jobs_with_scores,
    get_job_posting_by_id,
    update_job_posting,
)
from database import get_db
from models import User
from schemas import JobPosting, JobPostingCreate, ScoredJobResponse


router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    responses={404: {"description": "Not found"}},
)


@router.get("/scored", response_model=list[ScoredJobResponse])
async def list_scored_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return all saved jobs with their persisted score details, ordered
    newest-first (fetched_at DESC).

    **Authentication:** JWT bearer token required. Unauthenticated requests
    receive HTTP 401.

    **Ownership note:** The `jobs` and `scores` tables are global — they have
    no `user_id` column. Authentication prevents public access, but all
    authenticated users see the same pool of saved jobs. Per-user isolation
    would require a schema migration (adding `user_id` to `jobs`) which is
    outside the scope of this endpoint.

    **Unscored jobs:** Jobs whose scoring run failed (no row in `scores`) are
    included with `score=null`, `matched_skills=null`, `missing_skills=null`,
    `scored_at=null`, and `content_generation_available=false`.
    """
    rows = await get_all_jobs_with_scores(db)
    results: list[ScoredJobResponse] = []
    for job, score in rows:
        results.append(
            ScoredJobResponse(
                **JobPosting.model_validate(job).model_dump(),
                score=score.score if score else None,
                matched_skills=score.matched_skills if score else None,
                missing_skills=score.missing_skills if score else None,
                scored_at=score.scored_at if score else None,
                content_generation_available=(
                    should_trigger_content_generator(score.score)
                    if score else False
                ),
            )
        )
    return results


# NOTE: this route must remain AFTER /scored so FastAPI does not treat the
# literal string "scored" as a job_id path parameter.
@router.get("/{job_id}", response_model=JobPosting)
async def read_job(job_id: str, db: AsyncSession = Depends(get_db)):
    db_job = await get_job_posting_by_id(db, job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return db_job


@router.post("/", response_model=JobPosting)
async def create_job_endpoint(job: JobPostingCreate, db: AsyncSession = Depends(get_db)):
    return await create_job_posting(db, job)


@router.put("/{job_id}", response_model=JobPosting)
async def update_job_endpoint(
    job_id: str, updated_job: JobPostingCreate, db: AsyncSession = Depends(get_db)
):
    db_job = await update_job_posting(db, job_id, updated_job)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return db_job
