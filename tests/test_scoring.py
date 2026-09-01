import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from agent.scoring import (
    calculate_score,
    extract_required_skills,
    run_scoring,
)
from agent.scoring_runner import should_trigger_content_generator
from crud import (
    create_candidate_profile,
    create_job_posting,
    create_user_with_password,
    get_score_by_job_id,
)
from models import Base
from schemas import CandidateProfileCreate, JobPostingCreate, UserRegister


def test_score_math_deduplication_and_normalized_synonyms():
    score, matched, missing = calculate_score(
        ["Python", "SQL", "Docker", "ML", "javascript"],
        ["Python", "python", "SQL", "Kubernetes", "AWS", "Machine Learning", "JS"],
    )

    assert score == 67  # 4 of 6 distinct required skills
    assert matched == ["Python", "SQL", "Machine Learning", "JavaScript"]
    assert missing == ["Kubernetes", "Amazon Web Services"]


def test_score_zero_for_no_required_skills_and_inclusive_action_threshold():
    assert calculate_score(["Python"], [])[0] == 0
    assert should_trigger_content_generator(70) is True
    assert should_trigger_content_generator(71) is True


@pytest.mark.asyncio
async def test_job_extraction_normalizes_and_failure_becomes_empty_list(monkeypatch):
    class ExtractionResult:
        skills = ["Python", "ML", "python"]

    async def extractor(text: str, extraction_type: str) -> ExtractionResult:
        assert extraction_type == "job"
        if text == "unavailable":
            raise RuntimeError("provider unavailable")

        return ExtractionResult()

    monkeypatch.setattr("agent.scoring.extract_skills", extractor)

    assert await extract_required_skills("job text") == [
        "Python",
        "Machine Learning",
    ]
    assert await extract_required_skills("unavailable") == []


@pytest.mark.asyncio
async def test_run_scoring_uses_stored_candidate_skills_and_persists_score(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    class ExtractionResult:
        skills = ["Python", "SQL", "Kubernetes", "AWS"]

    async def extractor(text: str, extraction_type: str) -> ExtractionResult:
        assert extraction_type == "job"  # candidate extraction is never called here
        return ExtractionResult()

    monkeypatch.setattr("agent.scoring.extract_skills", extractor)

    async with session_factory() as session:
        user = await create_user_with_password(
            session,
            UserRegister(
                name="Candidate",
                email="candidate@example.com",
                password="Pass123!",
            ),
        )
        candidate = await create_candidate_profile(
            session,
            CandidateProfileCreate(
                role_preference=["Backend Developer"],
                preferred_location=["Delhi"],
                experience_years_min=1,
                experience_years_max=5,
                salary_min=500000,
                salary_max=1500000,
            ),
            user.id,
        )
        candidate.skills = ["Python", "SQL", "Docker"]
        await session.commit()
        job = await create_job_posting(
            session,
            JobPostingCreate(
                job_id="job-1",
                title="Backend Developer",
                company_name="Example",
                location="Delhi",
                platform="test",
                description="Python, SQL, Kubernetes and AWS required",
            ),
        )

        score = await run_scoring(job.job_id, candidate.id, session)
        stored_score = await get_score_by_job_id(session, job.job_id)

        assert score.score == 50
        assert score.matched_skills == ["Python", "SQL"]
        assert score.missing_skills == ["Kubernetes", "Amazon Web Services"]
        assert stored_score is not None

    await engine.dispose()
