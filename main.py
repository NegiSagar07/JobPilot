from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import engine
from models import Base
from router import agent, auth, candidate, content, jobs, resume, user


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(candidate.router)
app.include_router(jobs.router)
app.include_router(agent.router)
app.include_router(resume.router)
app.include_router(content.router)