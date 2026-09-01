from typing import TypedDict


class ResumeState(TypedDict):
    candidate_profile_id: int
    resume_file_path: str
    resume_text: str
    extracted_skills: list[str]