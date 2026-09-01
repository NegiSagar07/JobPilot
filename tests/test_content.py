"""
Integration tests for Content Generation Agent (agent/content/, router/content.py).
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from core.security import create_access_token
from crud import (
    create_candidate_profile,
    create_job_posting,
    create_score,
    create_user_with_password,
)
from database import get_db
from main import app
from models import Base
from schemas import CandidateProfileCreate, JobPostingCreate, ScoreCreate, UserRegister


def _make_engine():
    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _sample_job(job_id: str, title: str = "Senior Backend Engineer") -> JobPostingCreate:
    return JobPostingCreate(
        job_id=job_id,
        title=title,
        company_name="TechCorp",
        location="Remote",
        platform="indeed",
        is_remote=True,
        salary_min=1200000,
        salary_max=1800000,
        experience_required_years=4,
        description="Senior Backend Engineer proficient in Python, FastAPI, and PostgreSQL.",
    )


@pytest.mark.asyncio
async def test_content_generation_success_flow():
    """Test generating cover_letter, application_email, and recruiter_message for score >= 70."""
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
            UserRegister(name="Alice Tech", email="alice@test.com", password="Password123!"),
        )
        profile = await create_candidate_profile(
            session,
            CandidateProfileCreate(
                role_preference=["Backend Engineer"],
                preferred_location=["Remote"],
                experience_years_min=3,
                experience_years_max=6,
                salary_min=1000000,
                salary_max=2000000,
                remote_opt_in=True,
            ),
            user.id,
        )
        profile.skills = ["Python", "FastAPI", "PostgreSQL", "Docker"]
        await session.commit()

        job = await create_job_posting(session, _sample_job("job-high-score"))
        await create_score(
            session,
            ScoreCreate(
                job_id=job.job_id,
                score=85,
                matched_skills=["Python", "FastAPI", "PostgreSQL"],
                missing_skills=[],
            ),
        )
        token = create_access_token(data={"sub": user.email})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Generate Cover Letter
        res1 = await client.post(
            "/content/generate",
            headers=headers,
            json={"job_id": "job-high-score", "content_type": "cover_letter"},
        )
        assert res1.status_code == 201
        data1 = res1.json()
        assert data1["job_id"] == "job-high-score"
        assert data1["candidate_profile_id"] == profile.id
        assert data1["content_type"] == "cover_letter"
        assert len(data1["content"]) > 30

        # 2. Generate Application Email
        res2 = await client.post(
            "/content/generate",
            headers=headers,
            json={"job_id": "job-high-score", "content_type": "application_email"},
        )
        assert res2.status_code == 201
        data2 = res2.json()
        assert data2["content_type"] == "application_email"

        # 3. Generate Recruiter Message
        res3 = await client.post(
            "/content/generate",
            headers=headers,
            json={"job_id": "job-high-score", "content_type": "recruiter_message"},
        )
        assert res3.status_code == 201
        data3 = res3.json()
        assert data3["content_type"] == "recruiter_message"

        # 4. Check Content History Endpoint
        res_hist = await client.get("/content/job-high-score", headers=headers)
        assert res_hist.status_code == 200
        hist_data = res_hist.json()
        assert len(hist_data) == 3

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_content_generation_score_below_70_returns_403():
    """Test that score < 70 returns 403 Forbidden."""
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
            UserRegister(name="Bob Developer", email="bob@test.com", password="Password123!"),
        )
        profile = await create_candidate_profile(
            session,
            CandidateProfileCreate(
                role_preference=["Backend Engineer"],
                preferred_location=["Remote"],
                experience_years_min=2,
                experience_years_max=5,
                salary_min=800000,
                salary_max=1500000,
            ),
            user.id,
        )
        job = await create_job_posting(session, _sample_job("job-low-score"))
        # Score is 65 (below 70 threshold)
        await create_score(
            session,
            ScoreCreate(
                job_id=job.job_id,
                score=65,
                matched_skills=["Python"],
                missing_skills=["FastAPI", "PostgreSQL"],
            ),
        )
        token = create_access_token(data={"sub": user.email})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}
        res = await client.post(
            "/content/generate",
            headers=headers,
            json={"job_id": "job-low-score", "content_type": "cover_letter"},
        )
        assert res.status_code == 403
        assert "below required threshold of 70" in res.json()["detail"]

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_content_generation_unauthenticated_returns_401():
    """Test unauthenticated request returns 401."""
    engine = _make_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/content/generate",
            json={"job_id": "job-high-score", "content_type": "cover_letter"},
        )
        assert res.status_code == 401

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_content_generation_missing_job_or_profile_returns_404():
    """Test missing candidate profile or missing job returns 404."""
    engine = _make_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with session_maker() as session:
        # Case A: User without candidate profile
        user_no_prof = await create_user_with_password(
            session,
            UserRegister(name="No Profile", email="noprofile@test.com", password="Password123!"),
        )
        token_no_prof = create_access_token(data={"sub": user_no_prof.email})

        # Case B: User with candidate profile, but requesting non-existent job
        user_with_prof = await create_user_with_password(
            session,
            UserRegister(name="Has Profile", email="hasprofile@test.com", password="Password123!"),
        )
        await create_candidate_profile(
            session,
            CandidateProfileCreate(
                role_preference=["DevOps"],
                preferred_location=["Remote"],
                experience_years_min=1,
                experience_years_max=3,
                salary_min=500000,
                salary_max=1000000,
            ),
            user_with_prof.id,
        )
        token_with_prof = create_access_token(data={"sub": user_with_prof.email})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # User without profile -> 404
        res1 = await client.post(
            "/content/generate",
            headers={"Authorization": f"Bearer {token_no_prof}"},
            json={"job_id": "job-xyz", "content_type": "cover_letter"},
        )
        assert res1.status_code == 404
        assert res1.json()["detail"] == "Candidate profile not found"

        # User with profile requesting missing job -> 404
        res2 = await client.post(
            "/content/generate",
            headers={"Authorization": f"Bearer {token_with_prof}"},
            json={"job_id": "non-existent-job-id", "content_type": "cover_letter"},
        )
        assert res2.status_code == 404
        assert res2.json()["detail"] == "Job not found"

    app.dependency_overrides.clear()
    await engine.dispose()
