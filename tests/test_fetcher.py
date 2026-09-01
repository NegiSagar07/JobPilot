"""
Unit tests for LinkedIn Job Fetcher and .env configuration (agent/fetcher.py).
"""

from agent.fetcher import RateLimitException, fetch_linkedin_jobs
from core.config import settings


def test_env_config_loaded():
    assert settings.SECRET_KEY is not None
    assert settings.DATABASE_URL == "sqlite+aiosqlite:///./test.db"
    assert settings.MAX_JOBS_PER_RUN == 10
    assert settings.LINKEDIN_MOCK_MODE is True


def test_fetch_linkedin_jobs_batch_limit():
    jobs = fetch_linkedin_jobs(
        roles=["Python Developer"],
        locations=["Noida", "Delhi"],
        max_results=10,
    )
    assert len(jobs) == 10
    assert jobs[0].platform == "linkedin"


def test_fetch_linkedin_jobs_custom_limit():
    jobs = fetch_linkedin_jobs(
        roles=["Python Developer"],
        locations=["Noida", "Delhi"],
        max_results=5,
    )
    assert len(jobs) == 5


def test_fetch_linkedin_jobs_rate_limit_graceful_stop():
    # Simulates rate limiting triggering after 4 jobs
    jobs = fetch_linkedin_jobs(
        roles=["Python Developer"],
        locations=["Noida", "Delhi"],
        max_results=10,
        simulate_rate_limit_at=4,
    )
    # Should cleanly halt and return the 4 jobs fetched before rate limit
    assert len(jobs) == 4
