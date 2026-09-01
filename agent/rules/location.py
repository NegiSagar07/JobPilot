"""
Location Preference & Remote Opt-in Matching Rule (R2, R5, R68).
"""


def match_location(
    job_location: str,
    is_remote: bool,
    preferred_locations: list[str],
    remote_opt_in: bool = False,
) -> bool:
    """
    R2, R5, R68: Location & Remote Match.
    - If job is remote AND candidate opted in to remote, returns True (R5, R68).
    - Otherwise, checks if job_location matches any preferred location (case-insensitive).
    """
    if is_remote and remote_opt_in:
        return True

    if not job_location:
        return False

    job_loc_lower = job_location.lower().strip()

    if "remote" in job_loc_lower and remote_opt_in:
        return True

    if not preferred_locations:
        return False

    for loc in preferred_locations:
        loc_lower = loc.lower().strip()
        if loc_lower in job_loc_lower or job_loc_lower in loc_lower:
            return True

    return False
