"""
Salary Requirement Matching Rule (R4, R7, R8).
"""


def match_salary(
    job_salary_min: int | None,
    job_salary_max: int | None,
    cand_salary_min: int,
    cand_salary_max: int,
) -> bool:
    """
    R4, R7, R8: Salary Match.
    - R8: If job salary is missing (both min & max None), return True.
    - Checks if job salary range overlaps with candidate expected range [cand_min, cand_max].
    """
    if job_salary_min is None and job_salary_max is None:
        return True

    j_min = job_salary_min if job_salary_min is not None else job_salary_max
    j_max = job_salary_max if job_salary_max is not None else job_salary_min

    if j_min is None or j_max is None:
        return True

    # Range overlap check
    return j_max >= cand_salary_min and j_min <= cand_salary_max
