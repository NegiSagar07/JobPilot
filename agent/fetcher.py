"""
Job Search Agent — LinkedIn Job Fetcher Component (R60–R61)
Fetches all available mock listings unless an explicit source limit is provided.
Handles rate-limiting cleanly without in-run retries.
"""

import logging
from core.config import settings
from schemas import JobPostingBase

logger = logging.getLogger(__name__)


class RateLimitException(Exception):
    """Exception raised when LinkedIn rate-limits the agent (HTTP 429)."""

    pass


# Comprehensive seed dataset for LinkedIn mock mode
MOCK_LINKEDIN_JOBS: list[dict] = [
    {
        "title": "Python Developer",
        "company_name": "Tech Corp",
        "location": "Noida",
        "salary_min": 900000,
        "salary_max": 900000,
        "experience_required_years": 3,
        "apply_link": "https://linkedin.com/jobs/101",
        "platform": "linkedin",
        "is_remote": False,
    },
    {
        "title": "Backend Developer",
        "company_name": "Cloud Solutions",
        "location": "Delhi",
        "salary_min": 1000000,
        "salary_max": 1000000,
        "experience_required_years": 3,
        "apply_link": "https://linkedin.com/jobs/102",
        "platform": "linkedin",
        "is_remote": False,
    },
    {
        "title": "Senior Python Developer",
        "company_name": "Data Systems",
        "location": "Noida",
        "salary_min": 1100000,
        "salary_max": 1200000,
        "experience_required_years": 4,
        "apply_link": "https://linkedin.com/jobs/103",
        "platform": "linkedin",
        "is_remote": False,
    },
    {
        "title": "Python Developer",
        "company_name": "Gurgaon Tech",
        "location": "Gurgaon",
        "salary_min": 900000,
        "salary_max": 900000,
        "experience_required_years": 3,
        "apply_link": "https://linkedin.com/jobs/104",
        "platform": "linkedin",
        "is_remote": False,
    },
    {
        "title": "Python Developer",
        "company_name": "Global Remote Inc",
        "location": "Remote",
        "salary_min": 950000,
        "salary_max": 1050000,
        "experience_required_years": 3,
        "apply_link": "https://linkedin.com/jobs/105",
        "platform": "linkedin",
        "is_remote": True,
    },
    {
        "title": "Backend Engineer",
        "company_name": "SaaS Platform",
        "location": "Delhi",
        "salary_min": 850000,
        "salary_max": 950000,
        "experience_required_years": 2,
        "apply_link": "https://linkedin.com/jobs/106",
        "platform": "linkedin",
        "is_remote": False,
    },
    {
        "title": "Python Software Engineer",
        "company_name": "Innovate Ltd",
        "location": "Noida",
        "salary_min": 700000,
        "salary_max": 900000,
        "experience_required_years": 3,
        "apply_link": "https://linkedin.com/jobs/107",
        "platform": "linkedin",
        "is_remote": False,
    },
    {
        "title": "Backend Developer",
        "company_name": "Enterprise Systems",
        "location": "Delhi",
        "salary_min": None,  # R8: missing salary
        "salary_max": None,
        "experience_required_years": 3,
        "apply_link": "https://linkedin.com/jobs/108",
        "platform": "linkedin",
        "is_remote": False,
    },
    {
        "title": "Python Backend Developer",
        "company_name": "Startup Hub",
        "location": "Noida",
        "salary_min": 800000,
        "salary_max": 1000000,
        "experience_required_years": None,  # R9: missing experience
        "apply_link": "https://linkedin.com/jobs/109",
        "platform": "linkedin",
        "is_remote": False,
    },
    {
        "title": "Senior Backend Developer",
        "company_name": "FinTech Corp",
        "location": "Delhi",
        "salary_min": 1150000,
        "salary_max": 1200000,
        "experience_required_years": 3,
        "apply_link": "https://linkedin.com/jobs/110",
        "platform": "linkedin",
        "is_remote": False,
    },
    {
        "title": "Python Lead Developer",
        "company_name": "AI Solutions",
        "location": "Noida",
        "salary_min": 1200000,
        "salary_max": 1200000,
        "experience_required_years": 4,
        "apply_link": "https://linkedin.com/jobs/111",
        "platform": "linkedin",
        "is_remote": False,
    },
    {
        "title": "Backend Developer",
        "company_name": "Web Scale",
        "location": "Delhi",
        "salary_min": 900000,
        "salary_max": 1100000,
        "experience_required_years": 3,
        "apply_link": "https://linkedin.com/jobs/112",
        "platform": "linkedin",
        "is_remote": False,
    },
    {
        "title": "Backend Developer",
        "company_name": "Platform Works",
        "location": "Delhi",
        "salary_min": 950000,
        "salary_max": 1050000,
        "experience_required_years": 3,
        "apply_link": "https://linkedin.com/jobs/113",
        "platform": "linkedin",
        "is_remote": False,
    },
    {
        "title": "Python Developer",
        "company_name": "Data Services",
        "location": "Noida",
        "salary_min": 800000,
        "salary_max": 950000,
        "experience_required_years": 2,
        "apply_link": "https://linkedin.com/jobs/114",
        "platform": "linkedin",
        "is_remote": False,
    },
]


def fetch_linkedin_jobs(
    roles: list[str],
    locations: list[str],
    max_results: int | None = None,
    simulate_rate_limit_at: int | None = None,
) -> list[JobPostingBase]:
    """
    Fetches job listings from LinkedIn.
    Edge Case 60-61: If rate limiting occurs, cleanly halts and returns accumulated listings.
    """
    limit = max_results if max_results is not None else len(MOCK_LINKEDIN_JOBS)
    fetched_jobs: list[JobPostingBase] = []

    try:
        for idx, job_data in enumerate(MOCK_LINKEDIN_JOBS):
            if simulate_rate_limit_at is not None and idx >= simulate_rate_limit_at:
                raise RateLimitException("LinkedIn rate limit reached (HTTP 429)")

            if len(fetched_jobs) >= limit:
                break  # Reached the caller-specified source limit

            job = JobPostingBase(**job_data)
            fetched_jobs.append(job)

    except RateLimitException as exc:
        logger.warning(f"Fetch interrupted due to rate limit: {exc}. Returning accumulated jobs.")

    return fetched_jobs
