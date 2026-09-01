"""
Unit tests for Job Search Agent core filter engine (agent/filter.py)
Validates all Acceptance Criteria from SPECS.md.
"""

from agent.filter import (
    evaluate_job_posting,
    match_experience,
    match_location,
    match_role,
    match_salary,
    normalize_salary,
    parse_salary_string,
)
from schemas import CandidateProfileBase, JobPostingBase


def sample_candidate(remote_opt_in: bool = False) -> CandidateProfileBase:
    return CandidateProfileBase(
        resume_id=1,
        role_preference=["Backend Developer", "Python Developer"],
        preferred_location=["Delhi", "Noida"],
        experience_years_min=2,
        experience_years_max=4,
        salary_min=600000,   # 6 LPA
        salary_max=1200000,  # 12 LPA
        remote_opt_in=remote_opt_in,
    )



# ---------------------------------------------------------------------------
# Acceptance Criteria Tests (SPECS.md Section 7)
# ---------------------------------------------------------------------------

def test_ac_78_all_4_criteria_match():
    candidate = sample_candidate()
    job = JobPostingBase(
        title="Python Developer",
        company_name="Tech Corp",
        location="Noida",
        salary_min=900000,
        salary_max=900000,
        experience_required_years=3,
        apply_link="https://linkedin.com/jobs/1",
        platform="linkedin",
        is_remote=False,
    )
    assert evaluate_job_posting(job, candidate) is True


def test_ac_79_location_mismatch_fails():
    candidate = sample_candidate()
    job = JobPostingBase(
        title="Python Developer",
        company_name="Tech Corp",
        location="Gurgaon",
        salary_min=900000,
        salary_max=900000,
        experience_required_years=3,
        apply_link="https://linkedin.com/jobs/2",
        platform="linkedin",
        is_remote=False,
    )
    assert evaluate_job_posting(job, candidate) is False


def test_ac_80_backend_developer_delhi_matches():
    candidate = sample_candidate()
    job = JobPostingBase(
        title="Backend Developer",
        company_name="Cloud Solutions",
        location="Delhi",
        salary_min=1000000,
        salary_max=1000000,
        experience_required_years=3,
        apply_link="https://linkedin.com/jobs/3",
        platform="linkedin",
        is_remote=False,
    )
    assert evaluate_job_posting(job, candidate) is True


def test_ac_81_monthly_salary_normalization():
    # ₹80,000/month -> ₹9,60,000/year (within 6-12 LPA)
    sal_min, sal_max = parse_salary_string("₹80,000/month")
    assert sal_min == 960000
    assert sal_max == 960000

    candidate = sample_candidate()
    job = JobPostingBase(
        title="Python Developer",
        company_name="SaaS Inc",
        location="Delhi",
        salary_min=sal_min,
        salary_max=sal_max,
        experience_required_years=3,
        apply_link="https://linkedin.com/jobs/4",
        platform="linkedin",
        is_remote=False,
    )
    assert evaluate_job_posting(job, candidate) is True


def test_ac_82_missing_salary_fetches_anyway():
    candidate = sample_candidate()
    job = JobPostingBase(
        title="Backend Developer",
        company_name="Dev Corp",
        location="Delhi",
        salary_min=None,
        salary_max=None,
        experience_required_years=3,
        apply_link="https://linkedin.com/jobs/5",
        platform="linkedin",
        is_remote=False,
    )
    assert evaluate_job_posting(job, candidate) is True


def test_ac_83_missing_experience_fetches_anyway():
    candidate = sample_candidate()
    job = JobPostingBase(
        title="Backend Developer",
        company_name="Dev Corp",
        location="Delhi",
        salary_min=900000,
        salary_max=900000,
        experience_required_years=None,
        apply_link="https://linkedin.com/jobs/6",
        platform="linkedin",
        is_remote=False,
    )
    assert evaluate_job_posting(job, candidate) is True


def test_ac_84_remote_opt_in_fetches_remote_jobs():
    candidate = sample_candidate(remote_opt_in=True)
    job = JobPostingBase(
        title="Python Developer",
        company_name="Global Remote",
        location="Remote",
        salary_min=900000,
        salary_max=900000,
        experience_required_years=3,
        apply_link="https://linkedin.com/jobs/7",
        platform="linkedin",
        is_remote=True,
    )
    assert evaluate_job_posting(job, candidate) is True


def test_senior_developer_title_matches_preferred_role():
    candidate = sample_candidate()
    job = JobPostingBase(
        title="Senior Python Developer",
        company_name="Tech Corp",
        location="Noida",
        salary_min=900000,
        salary_max=900000,
        experience_required_years=3,
        apply_link="https://linkedin.com/jobs/8",
        platform="linkedin",
        is_remote=False,
    )
    assert evaluate_job_posting(job, candidate) is True


def test_experience_out_of_candidate_range_fails():
    candidate = sample_candidate()  # experience_min=2, experience_max=4
    job_over_exp = JobPostingBase(
        title="Python Developer",
        company_name="Tech Corp",
        location="Noida",
        salary_min=900000,
        salary_max=900000,
        experience_required_years=6,  # > 4 years, should fail
        apply_link="https://linkedin.com/jobs/9",
        platform="linkedin",
        is_remote=False,
    )
    assert evaluate_job_posting(job_over_exp, candidate) is False
    assert match_experience(job_exp=6, exp_min=2, exp_max=4) is False
    assert match_experience(job_exp=3, exp_min=2, exp_max=4) is True


def test_r14_role_matching_contiguous_phrase():
    preferred_roles = ["Backend Developer"]
    # Contiguous phrase match in Senior Backend Developer -> PASS
    assert match_role("Senior Backend Developer", preferred_roles) is True
    # Words appear separately in 'Backend Team Lead, Developer Relations' -> FAIL (R14)
    assert match_role("Backend Team Lead, Developer Relations", preferred_roles) is False


