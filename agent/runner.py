"""
Job Search Agent — Orchestrator & Runner Pipeline
Connects Fetcher -> Filter Engine -> Deduplication Engine -> Database Persistence.
Stops after saving settings.MAX_JOBS_PER_RUN new matching jobs.
"""

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from agent.dedup import generate_job_id, is_duplicate_job
from agent.fetcher import fetch_linkedin_jobs
from agent.filter import evaluate_job_posting
from agent.indeed_fetcher import IndeedScraperError, fetch_indeed_jobs
from agent.scoring import run_scoring
from agent.scoring_runner import should_trigger_content_generator
from core.config import settings
from crud import create_job_posting, get_candidate_profile_by_id
from schemas import CandidateProfile, JobPosting, JobPostingCreate


class ScoredJob(JobPosting):
    """A saved posting together with its deterministic candidate match."""

    score: int = Field(..., ge=0, le=100)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    content_generation_available: bool = Field(
        ...,
        description=(
            "Whether Cover Letter, Email, and Message actions are available "
            "for this score (score >= 70)."
        ),
    )


class AgentRunSummary(BaseModel):
    candidate_profile_id: int = Field(..., description="ID of the candidate profile evaluated")
    jobs_scanned: int = Field(..., description="Total fetched jobs evaluated before the run stopped")
    jobs_matched: int = Field(..., description="Total evaluated jobs passing all 4 criteria")
    jobs_saved: int = Field(..., description="New matching, non-duplicate jobs persisted to database")
    jobs_skipped_duplicate: int = Field(..., description="Matching jobs skipped because they were already in DB")
    saved_jobs: list[ScoredJob] = Field(
        default_factory=list,
        description="Newly saved jobs, including score and skill-match details.",
    )
    status: str = Field(..., description="Execution status e.g. 'completed'")


async def fetch_jobs_for_candidate(
    roles: list[str], locations: list[str]
):
    """Select the configured source without changing the rest of the pipeline."""
    if settings.JOB_SOURCE == "indeed":
        return await fetch_indeed_jobs(roles=roles, locations=locations)

    if settings.JOB_SOURCE == "mock":
        return fetch_linkedin_jobs(roles=roles, locations=locations, max_results=None)

    raise IndeedScraperError(
        "JOB_SOURCE must be either 'mock' or 'indeed'."
    )


async def run_job_search_agent(
    candidate_profile_id: int,
    db: AsyncSession,
) -> AgentRunSummary:
    """
    Executes the automated Job Search Agent run for a given candidate profile.
    1. Loads candidate preferences.
    2. Fetches raw job listings from the configured source.
    3. Evaluates 4-criteria strict AND filter engine.
    4. Computes SHA-256 job_id and skips duplicates.
    5. Persists up to MAX_JOBS_PER_RUN new matching jobs into DB, scanning
       every available fetched job until that save target is reached.
    """
    profile_orm = await get_candidate_profile_by_id(db, candidate_profile_id)
    if profile_orm is None:
        raise ValueError(f"CandidateProfile with id={candidate_profile_id} not found.")

    candidate = CandidateProfile.model_validate(profile_orm)

    raw_jobs = await fetch_jobs_for_candidate(
        roles=candidate.role_preference,
        locations=candidate.preferred_location,
    )

    jobs_scanned = 0
    jobs_matched = 0
    jobs_saved = 0
    jobs_skipped_duplicate = 0
    saved_jobs: list[ScoredJob] = []

    for raw_job in raw_jobs:
        # The run limit applies only to successful new saves, never to scans.
        if jobs_saved >= settings.MAX_JOBS_PER_RUN:
            break

        jobs_scanned += 1

        if not evaluate_job_posting(raw_job, candidate):
            continue

        jobs_matched += 1

        job_id = generate_job_id(
            company_name=raw_job.company_name,
            title=raw_job.title,
            location=raw_job.location,
            apply_link=raw_job.apply_link,
        )

        if await is_duplicate_job(db, job_id):
            jobs_skipped_duplicate += 1
            continue

        job_in = JobPostingCreate(
            job_id=job_id,
            **raw_job.model_dump(),
        )
        saved_job = await create_job_posting(db, job_in)
        score_row = await run_scoring(
            job_id=saved_job.job_id,
            candidate_profile_id=candidate_profile_id,
            db=db,
        )
        saved_jobs.append(
            ScoredJob(
                **JobPosting.model_validate(saved_job).model_dump(),
                score=score_row.score,
                matched_skills=score_row.matched_skills or [],
                missing_skills=score_row.missing_skills or [],
                content_generation_available=should_trigger_content_generator(
                    score_row.score
                ),
            )
        )
        jobs_saved += 1

    return AgentRunSummary(
        candidate_profile_id=candidate_profile_id,
        jobs_scanned=jobs_scanned,
        jobs_matched=jobs_matched,
        jobs_saved=jobs_saved,
        jobs_skipped_duplicate=jobs_skipped_duplicate,
        saved_jobs=saved_jobs,
        status="completed",
    )
