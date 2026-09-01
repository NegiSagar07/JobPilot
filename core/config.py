"""
Application Configuration Settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-jwt-key-for-job-autonomous-agent-2026")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    LINKEDIN_MOCK_MODE: bool = os.getenv("LINKEDIN_MOCK_MODE", "true").lower() == "true"
    MAX_JOBS_PER_RUN: int = int(os.getenv("MAX_JOBS_PER_RUN", "10"))

    # Job-source configuration. Keep mock as the default so a local/test run never
    # spends Apify credits unless the source is explicitly enabled.
    JOB_SOURCE: str = os.getenv("JOB_SOURCE", "mock").strip().lower()
    APIFY_API_TOKEN: str | None = os.getenv("APIFY_API_TOKEN")
    INDEED_COUNTRY: str = os.getenv("INDEED_COUNTRY", "IN").strip().upper()
    INDEED_MAX_ITEMS_PER_SEARCH: int = int(
        os.getenv("INDEED_MAX_ITEMS_PER_SEARCH", "10")
    )
    # Hard cap across every Apify Actor call in one agent run. Start small while
    # validating the integration to avoid spending credits unexpectedly.
    INDEED_MAX_ITEMS_PER_RUN: int = int(
        os.getenv("INDEED_MAX_ITEMS_PER_RUN", "3")
    )
    INDEED_MAX_SEARCHES_PER_RUN: int = int(
        os.getenv("INDEED_MAX_SEARCHES_PER_RUN", "1")
    )

    # Scoring Algorithm: required for production LLM skill extraction.  Tests
    # inject a deterministic extractor and never require this credential.
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-5-mini")


settings = Settings()
