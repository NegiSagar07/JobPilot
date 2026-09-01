from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from agent.resume.graph import build_resume_graph
from agent.resume.text_extractor import extract_text
from core.deps import get_current_user
from crud import (
    get_candidate_profile_by_user_id,
    upload_resume,
)
from database import get_db
from models import User, Resume
from schemas import ResumeUploadResponse


router = APIRouter(
    prefix="/resume",
    tags=["resume"],
)


UPLOAD_DIR = Path("uploads/resumes")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume_endpoint(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Find the candidate profile belonging to the authenticated user
    candidate = await get_candidate_profile_by_user_id(
        db,
        current_user.id,
    )

    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail="Candidate profile not found",
        )

    # 2. Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF resumes are supported",
        )

    # 3. Save the uploaded PDF
    filename = f"{uuid4()}.pdf"
    file_path = UPLOAD_DIR / filename

    contents = await file.read()
    file_path.write_bytes(contents)

    # 4. Create Resume database record
    resume = Resume(
        resume_file_path=str(file_path),
    )

    resume = await upload_resume(db, resume)

    # 5. Extract text from PDF
    resume_text = extract_text(file_path)

    if not resume_text:
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from resume",
        )

    # 6. Run the resume skill-extraction workflow
    graph = build_resume_graph(db)

    result = await graph.ainvoke(
        {
            "candidate_profile_id": candidate.id,
            "resume_file_path": str(file_path),
            "resume_text": resume_text,
            "extracted_skills": [],
        }
    )

    # 7. Associate the resume with the candidate profile
    candidate.resume_id = resume.id

    await db.commit()
    await db.refresh(candidate)

    return ResumeUploadResponse(
        resume_id=resume.id,
        candidate_profile_id=candidate.id,
        skills=result["extracted_skills"],
    )