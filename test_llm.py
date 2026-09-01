import asyncio

from agent.llm import extract_skills


async def main():
    resume_text = """
    Sagar is a Software Engineer with experience in Python, FastAPI,
    PostgreSQL, Docker, React, JavaScript and Git.
    He has also worked with REST APIs and Redis.
    """

    result = await extract_skills(resume_text)

    print("Extracted skills:")
    print(result.skills)


if __name__ == "__main__":
    asyncio.run(main())