"""
Job Search Agent — Core 4-Criteria Filter Engine (R1–R9)
Orchestrates individual match rules with strict AND evaluation logic.
"""

from agent.normalizers.salary import normalize_salary, parse_salary_string
from agent.rules.experience import match_experience
from agent.rules.location import match_location
from agent.rules.role import match_role
from agent.rules.salary import match_salary
from schemas import CandidateProfileBase, JobPostingBase


def evaluate_job_posting(
    job: JobPostingBase,
    candidate: CandidateProfileBase,
) -> bool:
    """
    R6: Strict 4-criteria AND match.
    Returns True ONLY IF role, location/remote, experience, AND salary all match.
    """
    if not match_role(job.title, candidate.role_preference):
        return False

    if not match_location(
        job_location=job.location,
        is_remote=job.is_remote,
        preferred_locations=candidate.preferred_location,
        remote_opt_in=candidate.remote_opt_in,
    ):
        return False

    if not match_experience(
        job_exp=job.experience_required_years,
        exp_min=candidate.experience_years_min,
        exp_max=candidate.experience_years_max,
    ):
        return False

    if not match_salary(
        job_salary_min=job.salary_min,
        job_salary_max=job.salary_max,
        cand_salary_min=candidate.salary_min,
        cand_salary_max=candidate.salary_max,
    ):
        return False

    return True


__all__ = [
    "normalize_salary",
    "parse_salary_string",
    "match_role",
    "match_location",
    "match_experience",
    "match_salary",
    "evaluate_job_posting",
]
