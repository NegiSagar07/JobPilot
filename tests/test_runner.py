"""
End-to-End Integration tests for Job Search Agent Runner (agent/runner.py, router/agent.py).
"""

import pytest
from types import SimpleNamespace
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.pool import StaticPool

import agent.runner as runner
from agent.dedup import generate_job_id
from agent.runner import run_job_search_agent
from core.security import create_access_token
from crud import (
    create_candidate_profile,
    create_job_posting,
    create_user_with_password,
)
from database import get_db
from main import app
from models import Base, JobPosting
from schemas import CandidateProfileCreate, JobPostingBase, JobPostingCreate, UserRegister


@pytest.mark.asyncio
async def test_end_to_end_agent_runner():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        user = await create_user_with_password(
            session,
            UserRegister(name="Alice", email="alice@example.com", password="Pass123!"),
        )
        cand_in = CandidateProfileCreate(
            role_preference=["Backend Developer", "Python Developer"],
            preferred_location=["Delhi", "Noida"],
            experience_years_min=2,
            experience_years_max=4,
            salary_min=600000,
            salary_max=1200000,
            remote_opt_in=True,
        )
        profile = await create_candidate_profile(session, cand_in, user.id)

        # First Run: Should scan through non-matches and save up to the configured limit.
        summary1 = await run_job_search_agent(candidate_profile_id=profile.id, db=session)
        assert summary1.jobs_saved == 10
        assert summary1.jobs_skipped_duplicate == 0
        assert summary1.status == "completed"

        # Verify DB records saved
        res = await session.execute(select(JobPosting))
        saved_jobs = res.scalars().all()
        assert len(saved_jobs) == 10

        # Second Run: Duplicate check should skip all 10 previously saved jobs
        summary2 = await run_job_search_agent(candidate_profile_id=profile.id, db=session)
        assert summary2.jobs_saved == 0
        assert summary2.jobs_skipped_duplicate == 10
        assert summary2.status == "completed"

    await engine.dispose()


@pytest.mark.asyncio
async def test_runner_scans_past_non_matches_and_duplicates_until_save_target(
    monkeypatch,
):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    def job(company_name: str, **overrides) -> JobPostingBase:
        values = {
            "title": "Backend Developer",
            "company_name": company_name,
            "location": "Delhi",
            "salary_min": 900000,
            "salary_max": 900000,
            "experience_required_years": 3,
            "apply_link": f"https://example.test/{company_name}",
            "platform": "test",
            "is_remote": False,
        }
        values.update(overrides)
        return JobPostingBase(**values)

    jobs = [
        job("role-failure", title="Frontend Developer"),
        job("duplicate"),
        job("location-failure", location="Gurgaon"),
        job("saved-one"),
        job("experience-failure", experience_required_years=5),
        job("saved-two"),
        job("salary-failure", salary_min=2000000, salary_max=2200000),
        job("saved-three"),
    ]

    async def fetch_test_jobs(roles, locations):
        return jobs

    scored_job_ids: list[str] = []

    async def score_test_job(job_id, candidate_profile_id, db):
        scored_job_ids.append(job_id)
        return SimpleNamespace(score=0, matched_skills=[], missing_skills=[])

    monkeypatch.setattr(runner, "fetch_jobs_for_candidate", fetch_test_jobs)
    monkeypatch.setattr(runner, "run_scoring", score_test_job)
    monkeypatch.setattr(runner.settings, "MAX_JOBS_PER_RUN", 3)

    async with session_maker() as session:
        user = await create_user_with_password(
            session,
            UserRegister(name="Alice", email="alice@example.com", password="Pass123!"),
        )
        profile = await create_candidate_profile(
            session,
            CandidateProfileCreate(
                role_preference=["Backend Developer"],
                preferred_location=["Delhi"],
                experience_years_min=2,
                experience_years_max=4,
                salary_min=600000,
                salary_max=1200000,
            ),
            user.id,
        )
        duplicate = jobs[1]
        await create_job_posting(
            session,
            JobPostingCreate(
                job_id=generate_job_id(
                    duplicate.company_name,
                    duplicate.title,
                    duplicate.location,
                    duplicate.apply_link,
                ),
                **duplicate.model_dump(),
            ),
        )

        summary = await run_job_search_agent(profile.id, session)

        assert summary.jobs_scanned == 8
        assert summary.jobs_matched == 4
        assert summary.jobs_skipped_duplicate == 1
        assert summary.jobs_saved == 3
        assert len(summary.saved_jobs) == 3
        assert len(scored_job_ids) == 3

    await engine.dispose()


@pytest.mark.asyncio
async def test_agent_api_endpoint():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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
            UserRegister(name="Alice", email="alice@example.com", password="Pass123!"),
        )
        cand_in = CandidateProfileCreate(
            role_preference=["Python Developer"],
            preferred_location=["Noida"],
            experience_years_min=2,
            experience_years_max=4,
            salary_min=600000,
            salary_max=1200000,
            remote_opt_in=False,
        )
        profile = await create_candidate_profile(session, cand_in, user.id)
        token = create_access_token(data={"sub": user.email})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Request without token should fail (401)
        res_unauth = await client.post("/agent/run")
        assert res_unauth.status_code == 401

        # Request with valid Bearer token
        headers = {"Authorization": f"Bearer {token}"}
        res_run = await client.post("/agent/run", headers=headers)
        assert res_run.status_code == 200
        summary = res_run.json()
        assert summary["candidate_profile_id"] == profile.id
        assert summary["jobs_saved"] > 0
        assert len(summary["saved_jobs"]) == summary["jobs_saved"]
        assert all("score" in job for job in summary["saved_jobs"])
        assert all("matched_skills" in job for job in summary["saved_jobs"])
        assert all("missing_skills" in job for job in summary["saved_jobs"])
        assert all("content_generation_available" in job for job in summary["saved_jobs"])
        assert summary["status"] == "completed"

    app.dependency_overrides.clear()
    await engine.dispose()
