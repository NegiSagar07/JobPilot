from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from agent.llm.client import extract_skills
from agent.resume.state import ResumeState
from agent.skill_normalization import normalize_skill
from crud import get_candidate_profile_by_id


async def extract_skills_node(state: ResumeState) -> dict:
    """
    Extract skills from the resume text using the LLM service.
    """

    result = await extract_skills(state["resume_text"])

    return {
        "extracted_skills": result.skills
    }


async def normalize_skills_node(state: ResumeState) -> dict:
    """
    Normalize and deduplicate extracted skills.
    """

    normalized_skills = []
    seen = set()

    for skill in state["extracted_skills"]:
        normalized = normalize_skill(skill)

        key = normalized.casefold()

        if key not in seen:
            seen.add(key)
            normalized_skills.append(normalized)

    return {
        "extracted_skills": normalized_skills
    }


def build_resume_graph(db: AsyncSession):
    """
    Build the LangGraph workflow for resume skill extraction.
    """

    async def persist_skills_node(state: ResumeState) -> dict:
        """
        Store the extracted skills in CandidateProfile.
        """

        candidate = await get_candidate_profile_by_id(
            db,
            state["candidate_profile_id"],
        )

        if candidate is None:
            raise ValueError(
                f"CandidateProfile with id={state['candidate_profile_id']} not found."
            )

        candidate.skills = state["extracted_skills"]

        await db.commit()
        await db.refresh(candidate)

        return {}

    graph = StateGraph(ResumeState)

    graph.add_node("extract_skills", extract_skills_node)
    graph.add_node("normalize_skills", normalize_skills_node)
    graph.add_node("persist_skills", persist_skills_node)

    graph.add_edge(START, "extract_skills")
    graph.add_edge("extract_skills", "normalize_skills")
    graph.add_edge("normalize_skills", "persist_skills")
    graph.add_edge("persist_skills", END)

    return graph.compile()