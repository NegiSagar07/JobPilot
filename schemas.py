from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class UserBase(BaseModel):
    name: str = Field(..., description="The name of the user")
    email: str = Field(..., description="The email address of the user")
    is_active: bool = Field(default=True, description="Whether the user is active")


class UserCreate(UserBase):
    password: str = Field(default="defaultpassword", description="The plain password for the user")


class UserRegister(BaseModel):
    name: str = Field(..., description="The name of the user")
    email: str = Field(..., description="The email address of the user")
    password: str = Field(..., description="The plain password for the user")


class UserLogin(BaseModel):
    email: str = Field(..., description="The email address of the user")
    password: str = Field(..., description="The plain password for the user")


class Token(BaseModel):
    access_token: str = Field(..., description="The JWT access token")
    token_type: str = Field(default="bearer", description="The token type")


class TokenData(BaseModel):
    email: str | None = Field(default=None, description="The subject email encoded in the token")


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="The unique identifier for the user")


class User(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="The unique identifier for the user")


class CandidateProfileBase(BaseModel):
    role_preference: list[str] = Field(..., description="List of preferred roles for the candidate")
    preferred_location: list[str] = Field(..., description="List of preferred locations for the candidate")
    experience_years_min: int = Field(..., description="Minimum expected experience in years (R3)")
    experience_years_max: int = Field(..., description="Maximum expected experience in years (R3)")
    salary_min: int = Field(..., description="Minimum expected yearly salary")
    salary_max: int = Field(..., description="Maximum expected yearly salary")
    remote_opt_in: bool = Field(default=False, description="Whether candidate accepts remote jobs regardless of location list")


class CandidateProfileCreate(CandidateProfileBase):
    pass


class CandidateProfile(CandidateProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="The unique identifier for the candidate profile")


class JobPostingBase(BaseModel):
    title: str = Field(..., description="The title of the job posting")
    company_name: str = Field(..., description="The name of the company posting the job")
    location: str = Field(..., description="The location of the job")

    # R8: salary may be missing on the source posting -> nullable
    salary_min: int | None = Field(None, description="Minimum yearly salary, normalized from monthly if needed (R7)")
    salary_max: int | None = Field(None, description="Maximum yearly salary, normalized from monthly if needed (R7)")

    # R9: experience may be missing on the source posting -> nullable
    experience_required_years: int | None = Field(None, description="Years of experience required, if listed")

    apply_link: str | None = Field(
        None,
        description="Direct application link, if exposed by the source posting",
    )
    platform: str = Field(..., description="Source platform this job was fetched from, e.g. 'indeed'")
    is_remote: bool = Field(default=False, description="Whether this posting is remote")
    description: str | None = Field(
        None,
        description="Raw job description text, stored for skill extraction and potential re-scoring",
    )
    required_skills: list[str] | None = Field(
        None,
        description="Normalized required skills extracted from description via LLM (S2). Null if none found or extraction failed (S5).",
    )


class JobPostingCreate(JobPostingBase):
    job_id: str = Field(..., description="Hash-based unique ID, generated at fetch time (dedup key)")


class JobPosting(JobPostingBase):
    model_config = ConfigDict(from_attributes=True)

    job_id: str = Field(..., description="Hash-based unique ID (primary key + dedup key)")
    fetched_at: datetime = Field(..., description="Timestamp when this job was fetched")


class ScoreBase(BaseModel):
    score: int = Field(
        ...,
        ge=0,
        le=100,
        description="(matched_skills / required_skills) * 100, per S4",
    )
    matched_skills: list[str] | None = Field(
        None,
        description="Skills present in both candidate and job",
    )
    missing_skills: list[str] | None = Field(
        None,
        description="Required skills candidate does not have",
    )


class ScoreCreate(ScoreBase):
    job_id: str = Field(..., description="Foreign key to jobs.job_id")


class Score(ScoreBase):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    scored_at: datetime



class ScoredJobResponse(JobPostingBase):
    """
    Saved job together with its persisted score details (read-only).

    Score fields are nullable: a job that has no score row (e.g. scoring
    failed) is still returned with null score values rather than hidden.
    content_generation_available defaults to False when score is absent.
    """

    model_config = ConfigDict(from_attributes=True)

    job_id: str = Field(..., description="Hash-based unique ID (primary key + dedup key)")
    fetched_at: datetime = Field(..., description="Timestamp when this job was fetched")

    # Score fields — None when no score row exists for this job
    score: int | None = Field(None, ge=0, le=100, description="Match score 0-100, null if not yet scored")
    matched_skills: list[str] | None = Field(None, description="Skills present in both candidate and job")
    missing_skills: list[str] | None = Field(None, description="Required skills the candidate lacks")
    scored_at: datetime | None = Field(None, description="When the score was last written")
    content_generation_available: bool = Field(
        False,
        description="True when score >= 70 (content generation threshold). False when unscored.",
    )


class ResumeUploadResponse(BaseModel):

    resume_id: int
    candidate_profile_id: int
    skills: list[str]
