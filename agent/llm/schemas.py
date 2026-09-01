from pydantic import BaseModel, Field


class SkillResponse(BaseModel):
    skills: list[str] = Field(
        description="List of technical and professional skills extracted from the text"
    )