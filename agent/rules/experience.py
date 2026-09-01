"""
Experience Requirement Matching Rule (R3, R9).
"""


def match_experience(
    job_exp: int | None,
    exp_min: int,
    exp_max: int,
) -> bool:
    """
    R3, R9: Experience Match.
    - R9: If job experience is missing/None, return True.
    - Returns True if job experience required falls within candidate experience range [exp_min, exp_max].
    """
    if job_exp is None:
        return True

    return exp_min <= job_exp <= exp_max

