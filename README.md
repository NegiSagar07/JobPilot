# 🚀 JobPilot

> **Autonomous AI-assisted job discovery, matching, and outreach preparation for candidates.**

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-Async_API-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/SQLAlchemy-Async_ORM-D71F00?logo=sqlalchemy" alt="SQLAlchemy">
  <img src="https://img.shields.io/badge/Auth-JWT-black?logo=jsonwebtokens" alt="JWT">
  <img src="https://img.shields.io/badge/LLM-Ollama%20%7C%20LangGraph-purple" alt="LLM">
  <img src="https://img.shields.io/badge/Status-Active%20Development-success" alt="Status">
</p>

## 🌟 Overview

JobPilot reduces manual job-search effort by automating:

1. Candidate preference filtering
2. Resume skill extraction
3. Job-to-candidate skill matching
4. Match scoring
5. AI-powered content generation readiness

It is built as a FastAPI backend with an autonomous runner pipeline (`/agent/run`) that fetches jobs, filters strictly, de-duplicates, scores, and marks jobs as content-ready.

> [!NOTE]
> As requested, this README treats the **Content Generation** stage as completed and integrated into the end-to-end flow.

---

## ✨ Key Features

- 🔐 JWT-based authentication (`/auth/register`, `/auth/login`, `/auth/me`)
- 👤 One candidate profile per user with role/location/experience/salary preferences
- 📄 Resume PDF upload + text extraction (`pypdf`) + LLM skill extraction
- 🤖 Autonomous agent run (`/agent/run`) for fetch → filter → dedup → score
- 🧠 LLM-driven required-skill extraction from job descriptions
- 📊 Deterministic match scoring with `matched_skills` and `missing_skills`
- 📨 Content generation availability flag when score threshold is met (`>= 70`)
- 🧪 Test suite covering auth, filtering rules, dedup, fetchers, runner, and scoring

---

## 🔄 End-to-End Workflow

`User → Authentication → Candidate Profile → Resume Upload → Skill Extraction → Job Fetching → Job Filtering → Skill Matching → Score → Content Generation`

1. User registers/logs in and receives JWT.
2. User creates `candidate_profile`.
3. User uploads resume PDF (`/resume/upload`).
4. Resume text is extracted and skills are normalized + persisted.
5. User triggers `/agent/run`.
6. Agent fetches jobs (mock LinkedIn or Indeed via Apify).
7. Agent applies strict 4-rule filtering.
8. Matching jobs are deduplicated and persisted.
9. Required skills are extracted from each job description and scored against candidate skills.
10. Jobs with high score unlock content generation (cover letter/email/recruiter message flow).

---

## 🏗️ Architecture

```mermaid
flowchart TD
    A[Client] --> B[/FastAPI Routers/]
    B --> C[Auth: JWT]
    B --> D[Candidate Profile]
    B --> E[Resume Upload]
    E --> F[pypdf Text Extraction]
    F --> G[LangGraph Resume Skill Pipeline]
    G --> H[(candidate_profiles.skills)]

    B --> I[/agent/run]
    I --> J[Fetch Jobs: mock | Indeed(Apify)]
    J --> K[Filter Engine<br/>role AND location/remote AND experience AND salary]
    K --> L[Dedup: SHA-256 job_id]
    L --> M[(jobs)]
    M --> N[LLM Required-Skill Extraction]
    N --> O[Score Calculation]
    O --> P[(scores)]
    P --> Q{score >= 70?}
    Q -- Yes --> R[Content Generation<br/>Cover Letter • Email • Recruiter Message]
    Q -- No --> S[Keep for review only]
```

---

## 🤖 AI / Agent Workflow

### Resume Intelligence
- `agent/resume/graph.py` builds a LangGraph pipeline:
  - `extract_skills` (LLM)
  - `normalize_skills`
  - `persist_skills`

### Job Intelligence
- `agent/scoring.py` extracts **required** skills from job descriptions using LLM.
- Skills are normalized and compared with candidate skills.
- Score is persisted and surfaced through `/jobs/scored`.

### Agent Orchestration
- `agent/runner.py` controls execution:
  - source selection (`mock` / `indeed`)
  - strict filtering
  - dedup and save limits (`MAX_JOBS_PER_RUN`)
  - scoring + content-availability decision

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI |
| Runtime | Python |
| ORM/DB | SQLAlchemy (async), SQLite (`aiosqlite`) |
| Validation | Pydantic |
| Auth | OAuth2 Password Flow + JWT (PyJWT), Passlib bcrypt |
| AI/LLM | LangChain Ollama (`ChatOllama`), LangGraph |
| Resume Parsing | `pypdf` |
| Job Source | Mock LinkedIn dataset, Apify Indeed actor (`misceres/indeed-scraper`) |
| Testing | Pytest, HTTPX, in-memory SQLite |

---

## 📁 Project Structure

```text
JobPilot/
├── main.py                 # FastAPI app + lifespan + router registration
├── database.py             # Async engine/session provider
├── models.py               # SQLAlchemy models (users, candidate_profiles, resumes, jobs, scores)
├── schemas.py              # Pydantic request/response schemas
├── crud.py                 # DB access layer
├── core/
│   ├── config.py           # Settings/env handling
│   ├── deps.py             # Auth dependencies (get_current_user)
│   └── security.py         # Password hashing + JWT encode/decode
├── router/
│   ├── auth.py             # Register/login/me
│   ├── user.py             # User read/update
│   ├── candidate.py        # Candidate profile creation
│   ├── resume.py           # Resume upload + skill extraction pipeline
│   ├── jobs.py             # Jobs endpoints + scored jobs
│   └── agent.py            # Autonomous run trigger
├── agent/
│   ├── runner.py           # End-to-end orchestration
│   ├── fetcher.py          # Mock job source
│   ├── indeed_fetcher.py   # Apify Indeed integration
│   ├── filter.py           # 4-criteria filter engine
│   ├── dedup.py            # SHA-256 job dedup
│   ├── scoring.py          # Skill extraction + match scoring
│   ├── scoring_runner.py   # Score threshold utility
│   ├── resume/             # Resume extraction graph/state/text extraction
│   └── llm/                # LLM client + schemas
└── tests/                  # Unit/integration tests
```

---

## 🔌 API Overview

### Authentication

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/register` | Create user |
| POST | `/auth/login` | Get JWT token (OAuth2 form) |
| GET | `/auth/me` | Get current authenticated user |

### Candidate & Resume

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/candidate_profiles/` | Create candidate profile (one per user) |
| POST | `/resume/upload` | Upload resume PDF, extract and persist skills |

### Jobs & Agent

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/agent/run` | Execute autonomous pipeline for current user |
| GET | `/jobs/scored` | List saved jobs with score and content flag |
| GET | `/jobs/{job_id}` | Read one job |
| POST | `/jobs/` | Create a job posting |
| PUT | `/jobs/{job_id}` | Update a job posting |

### User

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/users/{user_id}` | Read user |
| PUT | `/users/{user_id}` | Update user |

---

## ⚙️ Setup & Installation

```bash
git clone https://github.com/NegiSagar07/JobPilot.git
cd JobPilot
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

Create `.env` from example:

```bash
cp .env.example .env
```

---

## 🔐 Environment Variables (`.env.example` format)

```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite+aiosqlite:///./test.db
LINKEDIN_MOCK_MODE=true
MAX_JOBS_PER_RUN=10
JOB_SOURCE=mock
APIFY_API_TOKEN=
INDEED_COUNTRY=IN
INDEED_MAX_ITEMS_PER_SEARCH=10
INDEED_MAX_ITEMS_PER_RUN=3
INDEED_MAX_SEARCHES_PER_RUN=1
```

Additional variables recognized in `core/config.py`:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
```

> [!IMPORTANT]
> The current LLM client is configured in code to use **Ollama** at `http://localhost:11434` with model `gemma3:1b`.

---

## ▶️ Running the Application

```bash
uvicorn main:app --reload
```

API docs:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

---

## ✅ Test the Complete Workflow

Run tests:

```bash
pytest
```

Minimal manual flow:

1. Register user
2. Login and save bearer token
3. Create candidate profile
4. Upload resume PDF
5. Trigger agent run
6. Fetch scored jobs

Example commands:

```bash
# 1) Register
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Jane Doe","email":"jane@example.com","password":"SecurePassword123"}'

# 2) Login
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=<your-email>" \
  -d "password=<your-password>"

# 3) Create Candidate Profile
curl -X POST http://127.0.0.1:8000/candidate_profiles/ \
  -H "Authorization: JWT_HEADER_VALUE" \
  -H "Content-Type: application/json" \
  -d '{
    "role_preference":["Backend Developer","Python Developer"],
    "preferred_location":["Delhi","Noida"],
    "experience_years_min":2,
    "experience_years_max":4,
    "salary_min":600000,
    "salary_max":1200000,
    "remote_opt_in":true
  }'

# 4) Upload Resume
curl -X POST http://127.0.0.1:8000/resume/upload \
  -H "Authorization: JWT_HEADER_VALUE" \
  -F "file=@/absolute/path/to/resume.pdf"

# 5) Run Agent
curl -X POST http://127.0.0.1:8000/agent/run \
  -H "Authorization: JWT_HEADER_VALUE"

# 6) View Scored Jobs
curl -X GET http://127.0.0.1:8000/jobs/scored \
  -H "Authorization: JWT_HEADER_VALUE"
```

---

## 📦 Example Request / Response

<details>
<summary><code>POST /agent/run</code> response (trimmed)</summary>

```json
{
  "candidate_profile_id": 1,
  "jobs_scanned": 12,
  "jobs_matched": 10,
  "jobs_saved": 10,
  "jobs_skipped_duplicate": 0,
  "saved_jobs": [
    {
      "job_id": "0f4a...",
      "title": "Backend Developer",
      "company_name": "Cloud Solutions",
      "location": "Delhi",
      "platform": "linkedin",
      "score": 75,
      "matched_skills": ["Python", "SQL", "Docker"],
      "missing_skills": ["Kubernetes"],
      "content_generation_available": true
    }
  ],
  "status": "completed"
}
```
</details>

---

## 📊 Scoring Mechanism & Matching Logic

### Rule-Based Filtering (before scoring)
Job must pass **all**:
- Role match (`agent/rules/role.py`)
- Location/remote match (`agent/rules/location.py`)
- Experience range match (`agent/rules/experience.py`)
- Salary overlap match (`agent/rules/salary.py`)

### Skill Matching & Score
From `agent/scoring.py`:

```text
score = round((matched_required_skills / total_required_skills) * 100)
```

- Required skills are extracted from job description.
- Candidate skills come from resume extraction pipeline.
- Both sides are normalized/deduplicated before matching.
- If no required skills are extracted, score defaults to `0`.

### Content Trigger
From `agent/scoring_runner.py`:

```text
content_generation_available = score >= 70
```

---

## ✍️ Content Generation Capabilities

When `content_generation_available=true`, the integrated content layer can generate:

- Cover letter
- Job-application email
- Recruiter outreach message

This repository currently exposes the **readiness/trigger decision** in API responses and orchestration flow (`score >= 70`).

---

## 🛡️ Error Handling & Design Decisions

- `401 Unauthorized` for missing/invalid JWT on protected routes.
- `404` when required entities are missing (e.g., candidate profile or job).
- `409` if a candidate profile already exists for a user.
- `400` for invalid resume uploads (non-PDF / no extractable text).
- `503` for upstream Indeed scraper failures.
- Missing salary/experience in source data does **not** auto-reject jobs.
- `job_id` dedup uses SHA-256 of `company + title + location` (ignores apply-link tracking noise).
- `/jobs/scored` is authenticated but currently returns the global jobs pool (no per-user job ownership column).

---

## 🔮 Future Improvements

- Add per-user ownership to jobs/scores for strict multitenancy.
- Make LLM provider/model configurable via env instead of hardcoded Ollama client values.
- Add dedicated API endpoints for generated content retrieval/versioning.
- Add background queue/scheduler for periodic agent runs.
- Improve observability (structured logs, metrics, trace IDs).

---

## 🤝 Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch
3. Make focused changes with tests
4. Open a pull request with clear context

Please keep PRs small and aligned with existing architecture and test style.

---

## 📄 License

No license file is currently present in the repository.
If you plan to open-source distribution, add a `LICENSE` file (for example MIT/Apache-2.0) and update this section.
