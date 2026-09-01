"""
Unit tests for Job Search Agent Deduplication Engine (agent/dedup.py).
Validates SHA-256 hash generation determinism and database duplicate checks.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agent.dedup import generate_job_id, is_duplicate_job
from crud import create_job_posting
from models import Base
from schemas import JobPostingCreate


def test_generate_job_id_determinism():
    hash1 = generate_job_id("Tech Corp", "Python Developer", "Noida", "https://linkedin.com/jobs/1")
    hash2 = generate_job_id("Tech Corp", "Python Developer", "Noida", "https://linkedin.com/jobs/1")
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex digest length


def test_generate_job_id_normalization():
    # Different casing and whitespace should produce identical hash
    hash1 = generate_job_id("  Tech Corp ", "Python Developer ", " Noida ", "HTTPS://LINKEDIN.COM/JOBS/1 ")
    hash2 = generate_job_id("tech corp", "python developer", "noida", "https://linkedin.com/jobs/1")
    assert hash1 == hash2


def test_generate_job_id_different_listings():
    hash1 = generate_job_id("Tech Corp", "Python Developer", "Noida", "https://linkedin.com/jobs/1")
    hash2 = generate_job_id("Tech Corp", "Backend Developer", "Noida", "https://linkedin.com/jobs/1")
    assert hash1 != hash2


def test_generate_job_id_excludes_apply_link_r13():
    # Different tracking parameters in apply_link must produce identical hash (R13)
    hash1 = generate_job_id("Tech Corp", "Python Developer", "Noida", "https://linkedin.com/jobs/1?utm_source=feed")
    hash2 = generate_job_id("Tech Corp", "Python Developer", "Noida", "https://linkedin.com/jobs/1?trackingId=abc123xyz")
    assert hash1 == hash2


@pytest.mark.asyncio
async def test_is_duplicate_job_in_database():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        job_id = generate_job_id("Acme Inc", "Backend Engineer", "Delhi", "https://linkedin.com/jobs/100")

        # Check non-existent job
        assert await is_duplicate_job(session, job_id) is False

        # Create job
        job_in = JobPostingCreate(
            job_id=job_id,
            title="Backend Engineer",
            company_name="Acme Inc",
            location="Delhi",
            salary_min=800000,
            salary_max=1200000,
            experience_required_years=3,
            apply_link="https://linkedin.com/jobs/100",
            platform="linkedin",
            is_remote=False,
        )
        await create_job_posting(session, job_in)

        # Check existing job (duplicate)
        assert await is_duplicate_job(session, job_id) is True

    await engine.dispose()
