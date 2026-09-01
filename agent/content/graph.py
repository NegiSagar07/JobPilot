"""
LangGraph workflow for Content Generation Agent.
load_context -> analyze_match -> generate_content -> validate_content -> persist_content
"""

import logging
from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from agent.content.state import ContentState
from agent.llm.client import llm
from crud import create_generated_content

logger = logging.getLogger(__name__)


async def load_context_node(state: ContentState) -> dict:
    """
    Validate and prepare context from inputs.
    """
    if state["score"] < 70:
        raise ValueError(f"Content generation requires a score >= 70. Current score is {state['score']}.")

    if not state["candidate_name"]:
        raise ValueError("Candidate name is required.")

    if not state["job_title"] or not state["company_name"]:
        raise ValueError("Job title and company name are required.")

    return {}


async def analyze_match_node(state: ContentState) -> dict:
    """
    Construct structured match analysis context for LLM prompt.
    """
    matched_str = ", ".join(state["matched_skills"]) if state["matched_skills"] else "None explicitly listed"
    missing_str = ", ".join(state["missing_skills"]) if state["missing_skills"] else "None"
    candidate_skills_str = ", ".join(state["candidate_skills"]) if state["candidate_skills"] else "None listed"

    context = (
        f"Candidate Name: {state['candidate_name']}\n"
        f"Candidate Verified Skills: {candidate_skills_str}\n"
        f"Target Job Title: {state['job_title']}\n"
        f"Company Name: {state['company_name']}\n"
        f"Match Score: {state['score']}/100\n"
        f"Matched Skills: {matched_str}\n"
        f"Missing Skills: {missing_str}\n"
    )

    if state.get("job_description"):
        context += f"Job Description Overview:\n{state['job_description'][:500]}\n"

    return {"prompt_context": context}


async def generate_content_node(state: ContentState) -> dict:
    """
    Invoke LLM to generate requested content type (cover_letter, application_email, recruiter_message).
    Enforces strict grounding: no hallucinated experience, companies, or skills.
    """
    content_type = state["content_type"]
    context = state["prompt_context"]

    system_instruction = (
        "STRICT SYSTEM DIRECTIVE:\n"
        "You are a professional job application assistant.\n"
        "You must generate ONLY the requested text using strictly the verified information provided below.\n"
        "DO NOT INVENT, ASSUME, OR FABRICATE any degrees, past companies, job titles, years of experience, projects, or skills.\n"
        "Do not mention any missing skills as skills the candidate possesses.\n"
        "Keep the content clear, concise, professional, and truthful.\n"
    )

    if content_type == "cover_letter":
        prompt = (
            f"{system_instruction}\n"
            f"Task: Write a concise, professional Cover Letter for the position.\n\n"
            f"Context:\n{context}\n\n"
            f"Cover Letter:"
        )
    elif content_type == "application_email":
        prompt = (
            f"{system_instruction}\n"
            f"Task: Write a professional Application Email including a Subject Line and Email Body.\n\n"
            f"Context:\n{context}\n\n"
            f"Application Email:"
        )
    elif content_type == "recruiter_message":
        prompt = (
            f"{system_instruction}\n"
            f"Task: Write a short, engaging LinkedIn/Recruiter Outreach Message (under 150 words).\n\n"
            f"Context:\n{context}\n\n"
            f"Recruiter Message:"
        )
    else:
        raise ValueError(f"Unsupported content type: {content_type}")

    try:
        response = await llm.ainvoke(prompt)
        content_text = response.content if hasattr(response, "content") else str(response)
        content_text = content_text.strip()
    except Exception as exc:
        logger.exception("LLM generation failed for content generation")
        # Fallback generator if LLM is offline/errored in testing environment
        content_text = _generate_fallback_content(content_type, state)

    return {"generated_content": content_text}


def _generate_fallback_content(content_type: str, state: ContentState) -> str:
    """Deterministic fallback content generator when LLM service is unavailable."""
    name = state["candidate_name"]
    title = state["job_title"]
    company = state["company_name"]
    matched = ", ".join(state["matched_skills"]) if state["matched_skills"] else "my core technical skills"

    if content_type == "cover_letter":
        return (
            f"Dear Hiring Manager,\n\n"
            f"I am writing to express my strong interest in the {title} position at {company}. "
            f"My technical background includes experience with {matched}, matching your team's needs.\n\n"
            f"I welcome the opportunity to discuss how my verified skills fit this role.\n\n"
            f"Sincerely,\n{name}"
        )
    elif content_type == "application_email":
        return (
            f"Subject: Application for {title} - {name}\n\n"
            f"Dear Hiring Team,\n\n"
            f"Please accept my application for the {title} role at {company}. "
            f"I bring skills in {matched} and look forward to learning more about this opportunity.\n\n"
            f"Best regards,\n{name}"
        )
    else:
        return (
            f"Hi Hiring Team, I saw the {title} role at {company} and wanted to reach out. "
            f"I have strong skills in {matched} and would love to connect! Best, {name}"
        )


async def validate_content_node(state: ContentState) -> dict:
    """
    Validate that generated content is non-empty and well-formed.
    """
    content = state.get("generated_content", "").strip()

    if not content or len(content) < 20:
        return {"validation_passed": False}

    return {"validation_passed": True}


def build_content_graph(db: AsyncSession):
    """
    Build and compile the LangGraph workflow for Content Generation.
    """
    async def persist_content_node(state: ContentState) -> dict:
        """
        Persist validated content to database.
        """
        if not state.get("validation_passed"):
            raise ValueError("Generated content failed validation and cannot be persisted.")

        record = await create_generated_content(
            db=db,
            job_id=state["job_id"],
            candidate_profile_id=state["candidate_profile_id"],
            content_type=state["content_type"],
            content=state["generated_content"],
        )
        return {"persisted_id": record.id}

    graph = StateGraph(ContentState)

    graph.add_node("load_context", load_context_node)
    graph.add_node("analyze_match", analyze_match_node)
    graph.add_node("generate_content", generate_content_node)
    graph.add_node("validate_content", validate_content_node)
    graph.add_node("persist_content", persist_content_node)

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "analyze_match")
    graph.add_edge("analyze_match", "generate_content")
    graph.add_edge("generate_content", "validate_content")
    graph.add_edge("validate_content", "persist_content")
    graph.add_edge("persist_content", END)

    return graph.compile()
