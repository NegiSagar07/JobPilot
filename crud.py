from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.security import hash_password, verify_password
from models import CandidateProfile, JobPosting, Score, User
from schemas import (
    CandidateProfileCreate,
    JobPostingCreate,
    ScoreCreate,
    UserCreate,
    UserRegister,
)


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    user_data = user.model_dump()
    raw_password = user_data.pop("password", "defaultpassword")
    user_data["hashed_password"] = hash_password(raw_password)
    db_user = User(**user_data)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def create_user_with_password(db: AsyncSession, user_register: UserRegister) -> User:
    hashed_pwd = hash_password(user_register.password)
    db_user = User(
        name=user_register.name,
        email=user_register.email,
        hashed_password=hashed_pwd,
        is_active=True,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def update_user(db: AsyncSession, user_id: int, updated_user: UserCreate):
    existing_user = await get_user_by_id(db, user_id)
    if existing_user:
        for key, value in updated_user.model_dump().items():
            setattr(existing_user, key, value)
        await db.commit()
        await db.refresh(existing_user)
        return existing_user
    return None


async def delete_user(db: AsyncSession, user_id: int):
    existing_user = await get_user_by_id(db, user_id)
    if existing_user:
        await db.delete(existing_user)
        await db.commit()
        return True
    return False


async def upload_resume(db: AsyncSession, resume):
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    return resume



async def create_candidate_profile(
    db: AsyncSession, candidate_profile: CandidateProfileCreate, user_id: int
) -> CandidateProfile:
    db_candidate_profile = CandidateProfile(user_id=user_id, **candidate_profile.model_dump())
    db.add(db_candidate_profile)
    await db.commit()
    await db.refresh(db_candidate_profile)
    return db_candidate_profile


async def get_candidate_profile_by_id(
    db: AsyncSession, candidate_id: int
) -> CandidateProfile | None:
    result = await db.execute(
        select(CandidateProfile).filter(CandidateProfile.id == candidate_id)
    )
    return result.scalar_one_or_none()


async def get_candidate_profile_by_user_id(
    db: AsyncSession,
    user_id: int,
) -> CandidateProfile | None:
    result = await db.execute(
        select(CandidateProfile).filter(
            CandidateProfile.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def create_job_posting(
    db: AsyncSession, job_posting: JobPostingCreate
) -> JobPosting:
    db_job_posting = JobPosting(**job_posting.model_dump())
    db.add(db_job_posting)
    await db.commit()
    await db.refresh(db_job_posting)
    return db_job_posting



async def get_job_posting_by_id(db: AsyncSession, job_id: str):
    result = await db.execute(select(JobPosting).filter(JobPosting.job_id == job_id))
    return result.scalar_one_or_none()


async def update_job_posting(
    db: AsyncSession, job_id: str, updated_job: JobPostingCreate
) -> JobPosting | None:
    existing_job = await get_job_posting_by_id(db, job_id)
    if existing_job is None:
        return None

    for key, value in updated_job.model_dump(exclude={"job_id"}).items():
        setattr(existing_job, key, value)
    await db.commit()
    await db.refresh(existing_job)
    return existing_job


async def update_job_required_skills(
    db: AsyncSession, job_id: str, required_skills: list[str]
) -> JobPosting | None:
    """Persist LLM-extracted normalized required skills for one saved job."""
    job = await get_job_posting_by_id(db, job_id)
    if job is None:
        return None
    job.required_skills = required_skills
    await db.commit()
    await db.refresh(job)
    return job


async def get_score_by_job_id(db: AsyncSession, job_id: str) -> Score | None:
    result = await db.execute(select(Score).filter(Score.job_id == job_id))
    return result.scalar_one_or_none()


async def get_all_jobs_with_scores(
    db: AsyncSession,
) -> list[tuple[JobPosting, Score | None]]:
    """
    Return all saved jobs LEFT OUTER JOIN their score row, ordered by
    fetched_at DESC (newest first).

    Using an outer join means a job with no score row is still included —
    the Score element in the tuple will be None for such rows.
    One query; no per-job round-trips.
    """
    result = await db.execute(
        select(JobPosting, Score)
        .outerjoin(Score, JobPosting.job_id == Score.job_id)
        .order_by(JobPosting.fetched_at.desc())
    )
    return list(result.all())



async def create_score(db: AsyncSession, score: ScoreCreate) -> Score:
    """Create or replace the one score for a job, making event retries safe."""
    existing_score = await get_score_by_job_id(db, score.job_id)
    if existing_score is None:
        existing_score = Score(**score.model_dump())
        db.add(existing_score)
    else:
        existing_score.score = score.score
        existing_score.matched_skills = score.matched_skills
        existing_score.missing_skills = score.missing_skills
    await db.commit()
    await db.refresh(existing_score)
    return existing_score
