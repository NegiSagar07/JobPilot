"""
Integration tests for GET /jobs/scored (router/jobs.py).

Tests:
1. Authenticated request returns saved jobs with all score detail fields.
2. A job with score=70 has content_generation_available=True.
3. Unauthenticated request returns HTTP 401.
4. Existing GET /jobs/{job_id} behaviour is unchanged.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from core.security import create_access_token
from crud import create_candidate_profile, create_job_posting, create_score, create_user_with_password
from database import get_db
from main import app
from models import Base
from schemas import CandidateProfileCreate, JobPostingCreate, ScoreCreate, UserRegister


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_engine():
    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _sample_job(job_id: str, title: str = "Backend Developer") -> JobPostingCreate:
    return JobPostingCreate(
        job_id=job_id,
        title=title,
        company_name="ACME Corp",
        location="Delhi",
        platform="test",
        is_remote=False,
        salary_min=700_000,
        salary_max=1_200_000,
        experience_required_years=3,
        apply_link=f"https://example.test/{job_id}",
        description="Python, FastAPI, PostgreSQL",
    )


def _sample_score(job_id: str, score: int) -> ScoreCreate:
    return ScoreCreate(
        job_id=job_id,
        score=score,
        matched_skills=["Python", "FastAPI"],
        missing_skills=["Go"],
    )


# ---------------------------------------------------------------------------
# Test 1 — authenticated request returns jobs with score details
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scored_jobs_returns_jobs_with_score_details():
    engine = _make_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with session_maker() as session:
        user = await create_user_with_password(
            session,
            UserRegister(name="Bob", email="bob@test.com", password="Pass123!"),
        )
        await create_candidate_profile(
            session,
            CandidateProfileCreate(
                role_preference=["Backend Developer"],
                preferred_location=["Delhi"],
                experience_years_min=2,
                experience_years_max=5,
                salary_min=600_000,
                salary_max=1_500_000,
            ),
            user.id,
        )
        job1 = await create_job_posting(session, _sample_job("job-aaa", "Backend Developer"))
        job2 = await create_job_posting(session, _sample_job("job-bbb", "Python Developer"))
        await create_score(session, _sample_score(job1.job_id, score=80))
        await create_score(session, _sample_score(job2.job_id, score=55))
        token = create_access_token(data={"sub": user.email})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}
        res = await client.get("/jobs/scored", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 2

    # Every item must carry all required fields
    for item in data:
        assert "job_id" in item
        assert "title" in item
        assert "score" in item
        assert "matched_skills" in item
        assert "missing_skills" in item
        assert "scored_at" in item
        assert "content_generation_available" in item

    app.dependency_overrides.clear()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Test 2 — score == 70 sets content_generation_available = True
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_score_70_sets_content_generation_available():
    engine = _make_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with session_maker() as session:
        user = await create_user_with_password(
            session,
            UserRegister(name="Carol", email="carol@test.com", password="Pass123!"),
        )
        await create_candidate_profile(
            session,
            CandidateProfileCreate(
                role_preference=["Backend Developer"],
                preferred_location=["Delhi"],
                experience_years_min=2,
                experience_years_max=5,
                salary_min=600_000,
                salary_max=1_500_000,
            ),
            user.id,
        )
        # Score exactly at the threshold
        job_at = await create_job_posting(session, _sample_job("job-at-70"))
        await create_score(session, ScoreCreate(
            job_id=job_at.job_id, score=70,
            matched_skills=["Python"], missing_skills=[],
        ))
        # Score one below the threshold
        job_below = await create_job_posting(session, _sample_job("job-below-70"))
        await create_score(session, ScoreCreate(
            job_id=job_below.job_id, score=69,
            matched_skills=[], missing_skills=["Python"],
        ))
        token = create_access_token(data={"sub": user.email})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}
        res = await client.get("/jobs/scored", headers=headers)

    assert res.status_code == 200
    data = res.json()
    by_id = {item["job_id"]: item for item in data}

    assert by_id["job-at-70"]["content_generation_available"] is True
    assert by_id["job-below-70"]["content_generation_available"] is False

    app.dependency_overrides.clear()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Test 3 — unauthenticated request returns 401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scored_jobs_unauthenticated_returns_401():
    engine = _make_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # No Authorization header
        res = await client.get("/jobs/scored")

    assert res.status_code == 401

    app.dependency_overrides.clear()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Test 4 — existing GET /jobs/{job_id} is unchanged (no score fields)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_job_by_id_unchanged():
    engine = _make_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with session_maker() as session:
        job = await create_job_posting(session, _sample_job("job-xyz", "Data Engineer"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(f"/jobs/{job.job_id}")

    assert res.status_code == 200
    data = res.json()

    # Must contain standard job fields
    assert data["job_id"] == "job-xyz"
    assert data["title"] == "Data Engineer"
    assert "fetched_at" in data

    # Must NOT contain score fields — this is the plain JobPosting schema
    assert "score" not in data
    assert "content_generation_available" not in data
    assert "scored_at" not in data

    app.dependency_overrides.clear()
    await engine.dispose()
