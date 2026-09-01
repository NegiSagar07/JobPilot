from collections.abc import Sequence
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from agent.llm.client import extract_skills
from agent.skill_normalization import normalize_skill
from crud import (
    create_score,
    get_candidate_profile_by_id,
    get_job_posting_by_id,
    update_job_required_skills,
)
from schemas import ScoreCreate


logger = logging.getLogger(__name__)


def _deduplicated_normalized_skills(
    skills: Sequence[str] | None,
) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()

    for skill in skills or []:
        if not isinstance(skill, str) or not skill.strip():
            continue

        canonical_skill = normalize_skill(skill)
        comparison_key = canonical_skill.casefold()

        if comparison_key not in seen:
            seen.add(comparison_key)
            unique.append(canonical_skill)

    return unique


async def extract_required_skills(
    job_description: str | None,
) -> list[str]:

    if not job_description:
        return []

    try:
        result = await extract_skills(
            job_description,
            extraction_type="job",
        )
    except Exception:
        # A job must remain visible and score as zero when the extraction
        # provider is unavailable or cannot process its description.
        logger.exception("Unable to extract required skills for a job description")
        return []

    return _deduplicated_normalized_skills(result.skills)


def calculate_score(
    candidate_skills: Sequence[str] | None,
    required_skills: Sequence[str] | None,
) -> tuple[int, list[str], list[str]]:

    candidate = _deduplicated_normalized_skills(candidate_skills)
    required = _deduplicated_normalized_skills(required_skills)

    if not required:
        return 0, [], []

    candidate_keys = {
        skill.casefold()
        for skill in candidate
    }

    matched_skills = [
        skill
        for skill in required
        if skill.casefold() in candidate_keys
    ]

    missing_skills = [
        skill
        for skill in required
        if skill.casefold() not in candidate_keys
    ]

    score = round(
        (len(matched_skills) / len(required)) * 100
    )

    return score, matched_skills, missing_skills


async def run_scoring(
    job_id: str,
    candidate_profile_id: int,
    db: AsyncSession,
):
    """
    Score one job against the current candidate.
    """

    # 1. Get job
    job = await get_job_posting_by_id(
        db,
        job_id,
    )

    if job is None:
        raise ValueError(
            f"JobPosting with id={job_id} not found."
        )

    # 2. Get current candidate
    candidate = await get_candidate_profile_by_id(
        db,
        candidate_profile_id,
    )

    if candidate is None:
        raise ValueError(
            f"CandidateProfile with id={candidate_profile_id} not found."
        )

    # 3. Extract required skills from job description
    required_skills = await extract_required_skills(
        job.description
    )

    # 4. Save required skills to job
    await update_job_required_skills(
        db,
        job_id,
        required_skills,
    )

    # 5. Calculate score
    score, matched_skills, missing_skills = calculate_score(
        candidate.skills,
        required_skills,
    )

    # 6. Save score
    score_row = await create_score(
        db,
        ScoreCreate(
            job_id=job_id,
            score=score,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
        ),
    )

    return score_row
