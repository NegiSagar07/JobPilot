"""
Job Search Agent — Deduplication Engine & Job ID Hashing (R10)
Generates deterministic SHA-256 job_id hashes and checks for database duplicates.
"""

import hashlib
from sqlalchemy.ext.asyncio import AsyncSession

from crud import get_job_posting_by_id


def generate_job_id(
    company_name: str,
    title: str,
    location: str,
    apply_link: str | None = None,
) -> str:
    """
    R10, R13: Generates a SHA-256 hash string serving as job_id.
    Hashes company_name + title + location only (lowercased, stripped).
    apply_link is deliberately EXCLUDED to prevent dynamic tracking parameter mismatches (R13).
    """
    norm_company = (company_name or "").strip().lower()
    norm_title = (title or "").strip().lower()
    norm_location = (location or "").strip().lower()

    raw_string = f"{norm_company}|{norm_title}|{norm_location}"
    return hashlib.sha256(raw_string.encode("utf-8")).hexdigest()


async def is_duplicate_job(db: AsyncSession, job_id: str) -> bool:
    """
    R10: Returns True if job_id already exists in the database.
    """
    existing_job = await get_job_posting_by_id(db, job_id)
    return existing_job is not None
