import re
from collections.abc import Iterable
from typing import Any

from agent.normalizers.salary import parse_salary_string
from core.config import settings
from schemas import JobPostingBase

ACTOR_ID = "misceres/indeed-scraper"


class IndeedScraperError(RuntimeError):
    """Raised when the Apify Indeed source cannot return a usable result."""


def extract_experience(description: str | None) -> int | None:
    if not description:
        return None

    match = re.search(r"\b(\d+)\s*(?:\+?\s*)?(?:years?|yrs?)\b", description, re.I)
    return int(match.group(1)) if match else None


def map_indeed_item(item: dict) -> JobPostingBase | None:
    if item.get("error") or not item.get("positionName") or not item.get("company"):
        return None

    title = str(item["positionName"]).strip()
    company_name = str(item["company"]).strip()
    location = (item.get("location") or "Unknown").strip()
    description = item.get("description") or ""

    salary_min, salary_max = parse_salary_string(item.get("salary") or "")
    is_remote = "remote" in location.lower() or "remote" in description.lower()

    return JobPostingBase(
        title=title,
        company_name=company_name,
        location=location,
        salary_min=salary_min,
        salary_max=salary_max,
        experience_required_years=extract_experience(description),
        apply_link=item.get("externalApplyLink") or item.get("url"),
        platform="indeed",
        is_remote=is_remote,
        description=description,
    )


async def fetch_indeed_jobs(
    roles: list[str],
    locations: list[str],
    *,
    client: Any | None = None,
) -> list[JobPostingBase]:
    """Run the Apify actor for each role/location pair and map its dataset."""
    if not roles or not locations:
        return []

    if client is None:
        if not settings.APIFY_API_TOKEN:
            raise IndeedScraperError(
                "APIFY_API_TOKEN is required when JOB_SOURCE=indeed."
            )
        try:
            from apify_client import ApifyClientAsync
        except ImportError as exc:
            raise IndeedScraperError(
                "The Apify client is not installed. Run: pip install apify-client"
            ) from exc
        client = ApifyClientAsync(settings.APIFY_API_TOKEN)

    async def search(
        role: str, location: str, max_items: int
    ) -> list[JobPostingBase]:
        try:
            run = await client.actor(ACTOR_ID).call(run_input={
                "position": role,
                "location": location,
                "country": settings.INDEED_COUNTRY,
                "maxItems": max_items,
                "saveOnlyUniqueItems": True,
            })
            if run is None:
                return []

            result = await client.dataset(run["defaultDatasetId"]).list_items()
        except Exception as exc:
            raise IndeedScraperError(
                f"Indeed search failed for role={role!r}, location={location!r}."
            ) from exc

        items: Iterable[dict] = getattr(result, "items", [])
        return [job for item in items if (job := map_indeed_item(item)) is not None]

    searches = [
        (role, location)
        for role in roles
        for location in locations
    ][:max(1, settings.INDEED_MAX_SEARCHES_PER_RUN)]

    remaining = max(0, settings.INDEED_MAX_ITEMS_PER_RUN)
    jobs: list[JobPostingBase] = []
    for role, location in searches:
        if remaining == 0:
            break

        requested_items = min(settings.INDEED_MAX_ITEMS_PER_SEARCH, remaining)
        search_jobs = await search(role, location, requested_items)
        jobs.extend(search_jobs[:remaining])
        remaining = settings.INDEED_MAX_ITEMS_PER_RUN - len(jobs)

    return jobs
