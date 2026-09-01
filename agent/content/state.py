from typing import TypedDict


class ContentState(TypedDict):
    """
    Structured generation state for Content Generation Agent workflow.
    """
    # Candidate information
    candidate_profile_id: int
    candidate_name: str
    candidate_skills: list[str]

    # Job information
    job_id: str
    job_title: str
    company_name: str
    job_description: str | None
    required_skills: list[str]

    # Scoring information
    score: int
    matched_skills: list[str]
    missing_skills: list[str]

    # Generation parameters & state
    content_type: str  # cover_letter | application_email | recruiter_message
    prompt_context: str
    generated_content: str
    validation_passed: bool
    persisted_id: int | None
