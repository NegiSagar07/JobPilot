from types import SimpleNamespace

import pytest

from agent.indeed_fetcher import fetch_indeed_jobs, map_indeed_item
from core.config import settings


def test_map_indeed_item_normalizes_supported_fields():
    job = map_indeed_item({
        "positionName": "Senior Python Developer",
        "company": "Example Labs",
        "location": "Noida, Uttar Pradesh",
        "salary": "₹80,000/month",
        "description": "Requires 3+ years of Python experience. Remote work available.",
        "url": "https://indeed.example/jobs/123",
    })

    assert job is not None
    assert job.title == "Senior Python Developer"
    assert job.company_name == "Example Labs"
    assert (job.salary_min, job.salary_max) == (960000, 960000)
    assert job.experience_required_years == 3
    assert job.apply_link == "https://indeed.example/jobs/123"
    assert job.platform == "indeed"
    assert job.is_remote is True
    assert job.description == "Requires 3+ years of Python experience. Remote work available."


def test_map_indeed_item_skips_actor_error_items():
    assert map_indeed_item({"error": "FOUND_NO_RESULTS"}) is None


class FakeActor:
    def __init__(self, calls):
        self.calls = calls

    async def call(self, *, run_input):
        self.calls.append(run_input)
        return {"defaultDatasetId": "dataset-1"}


class FakeDataset:
    async def list_items(self):
        return SimpleNamespace(items=[{
            "positionName": "Python Developer",
            "company": "Example Labs",
            "location": "Noida",
            "salary": "9 LPA",
            "description": "3 years of experience",
            "externalApplyLink": "https://company.example/apply",
        }])


class FakeApifyClient:
    def __init__(self):
        self.calls = []

    def actor(self, actor_id):
        assert actor_id == "misceres/indeed-scraper"
        return FakeActor(self.calls)

    def dataset(self, dataset_id):
        assert dataset_id == "dataset-1"
        return FakeDataset()


@pytest.mark.asyncio
async def test_fetch_indeed_jobs_runs_actor_and_maps_its_dataset(monkeypatch):
    client = FakeApifyClient()
    monkeypatch.setattr(settings, "INDEED_COUNTRY", "IN")
    monkeypatch.setattr(settings, "INDEED_MAX_ITEMS_PER_SEARCH", 7)
    monkeypatch.setattr(settings, "INDEED_MAX_ITEMS_PER_RUN", 3)
    monkeypatch.setattr(settings, "INDEED_MAX_SEARCHES_PER_RUN", 8)

    jobs = await fetch_indeed_jobs(
        roles=["Python Developer"],
        locations=["Noida"],
        client=client,
    )

    assert len(jobs) == 1
    assert jobs[0].apply_link == "https://company.example/apply"
    assert client.calls == [{
        "position": "Python Developer",
        "location": "Noida",
        "country": "IN",
        "maxItems": 3,
        "saveOnlyUniqueItems": True,
    }]


@pytest.mark.asyncio
async def test_fetch_indeed_jobs_stops_after_total_run_budget(monkeypatch):
    client = FakeApifyClient()
    monkeypatch.setattr(settings, "INDEED_MAX_ITEMS_PER_SEARCH", 10)
    monkeypatch.setattr(settings, "INDEED_MAX_ITEMS_PER_RUN", 3)
    monkeypatch.setattr(settings, "INDEED_MAX_SEARCHES_PER_RUN", 8)

    jobs = await fetch_indeed_jobs(
        roles=["Python Developer", "Backend Developer"],
        locations=["Noida", "Delhi"],
        client=client,
    )

    assert len(jobs) == 3
    assert len(client.calls) == 3
    assert all(call["maxItems"] <= 3 for call in client.calls)
