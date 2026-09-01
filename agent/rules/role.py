"""
Role Preference Matching Rule (R1).
"""


import re


def match_role(job_title: str, preferred_roles: list[str]) -> bool:
    """
    R1, R14: Role Match.
    Matches if any preferred role string appears as a contiguous whole word/phrase match in job_title (case-insensitive).
    E.g. 'Backend Developer' matches 'Senior Backend Developer', but does NOT match 'Backend Team Lead - Developer Relations'.
    """
    if not job_title or not preferred_roles:
        return False

    title_lower = job_title.lower()
    for role in preferred_roles:
        role_clean = role.strip().lower()
        if not role_clean:
            continue
        pattern = r"\b" + re.escape(role_clean) + r"\b"
        if re.search(pattern, title_lower):
            return True
    return False
