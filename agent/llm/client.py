from langchain_ollama import ChatOllama

from agent.llm.schemas import SkillResponse


llm = ChatOllama(
    model="gemma3:1b",
    base_url="http://localhost:11434",
    temperature=0,
)

structured_llm = llm.with_structured_output(SkillResponse)


async def extract_skills(
    text: str,
    extraction_type: str = "resume",
) -> SkillResponse:

    if extraction_type == "resume":

        prompt = f"""
You are a resume skill extraction system.

Extract only the technical and professional skills that
the candidate explicitly possesses or has experience with.

Do not extract:
- education
- job titles
- companies
- years of experience
- projects
- achievements
- responsibilities
- general descriptions

Return only the candidate's skills.

Resume:
{text}
"""

    elif extraction_type == "job":

        prompt = f"""
You are a job description skill extraction system.

Extract only the technical and professional skills that are
REQUIRED for this job.

Include skills explicitly described as:
- required
- must have
- mandatory
- essential
- required experience with

Do NOT include:
- education
- job titles
- companies
- years of experience
- projects
- achievements
- responsibilities
- optional skills
- preferred skills
- nice-to-have skills
- general descriptions

If a skill is mentioned only as preferred, optional,
or nice-to-have, do not include it.

Return only the required skills.

Job Description:
{text}
"""

    else:
        raise ValueError(
            f"Unsupported extraction type: {extraction_type}"
        )

    result = await structured_llm.ainvoke(prompt)

    return result