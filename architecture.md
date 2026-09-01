Job Search Agent — System Architecture Document

1. System Overview & Problem Statement

Candidates manually search and filter job listings across platforms such as Indeed against their specific role, location, salary, and experience preferences before reading job descriptions. This process is repetitive, error-prone, and time-consuming.

The Job Search Agent automates this pre-filtering stage by operating as a strict, rule-based screening pipeline. It replicates a candidate's manual filtering decisions before downstream skill extraction and resume-fit scoring evaluate the candidate's actual qualifications.

2. System Scope & Boundaries

In Scope

Target Platform: Indeed job listings via Apify v1.

Fetcher: Apify misceres/indeed-scraper Actor.

Candidate Preferences: Role list, location list, experience range in years, annual salary range in LPA / INR, and an independent remote-job opt-in toggle.

Strict filtering: Role AND Location/Remote AND Experience AND Salary must satisfy the filter. Missing experience and missing salary do not exclude a job.

Salary Normalization: Monthly salary quotes are converted to annual figures before range comparison.

Role Matching: Case-insensitive contiguous whole-word/phrase matching.

Remote Matching: When remote opt-in is enabled, remote jobs pass regardless of the candidate's location list.

Missing Field Tolerance: Missing salary, missing experience, and missing apply link do not cause a job to be discarded.

Deterministic Deduplication: SHA-256 job_id based only on company name, title, and location.

Database Persistence: Matching, non-duplicate jobs are stored asynchronously.

Downstream Event: A newly persisted job can trigger the downstream scoring pipeline.

Out of Scope / Non-Goals

Resume fit-scoring logic itself.

Skill extraction logic itself.

Cover letter, email, LinkedIn, or WhatsApp content generation.

Candidate approval/edit workflow.

Automatic job application.

Platforms beyond Indeed.

In-run retries after rate limiting.

Scheduling/execution frequency; deferred to a later decision.

3. High-Level System Architecture

graph TD

    Client["Client / API Consumer"] -->|POST /agent/run/{profile_id}| API["FastAPI Router Layer"]

    API -->|Authenticate & Load Profile| DB_Load[("Database / AsyncSession")]
    DB_Load -->|CandidateProfile| AgentRunner["Job Search Agent Runner"]

    subgraph Job Search Agent
        AgentRunner -->|1. Fetch Raw Listings| Fetcher["Indeed / Apify Fetcher"]

        Fetcher -->|Raw Job Listings| FilterEngine["4-Criteria Filter Engine"]

        subgraph Filter Engine
            FilterEngine --> RuleRole["Role Rule"]
            FilterEngine --> RuleLoc["Location / Remote Rule"]
            FilterEngine --> RuleExp["Experience Rule"]
            FilterEngine --> RuleSal["Salary Rule / Normalizer"]
        end

        FilterEngine -->|Passed Jobs| DedupEngine["Deduplication Engine"]

        DedupEngine -->|Check job_id| DB_Check[("Database")]
        DedupEngine -->|New Matched Job| DB_Save[("jobs table")]
    end

    DB_Save -->|Job Created Event| SkillExtractor["Required Skill Extraction"]
    SkillExtractor --> Scoring["Scoring Component"]

    Scoring -->|score < 70| End["No Content Generation"]
    Scoring -->|score >= 70| ContentGenerator["Content Generator"]

    ContentGenerator --> Approval["Candidate Approval / Edit"]
    Approval -->|Approved| ApplicationAgent["Application Agent"]
    Approval -->|Edit| Approval

    AgentRunner -->|AgentRunSummary| API
    API -->|JSON Response| Client

4. Pipeline & Control Flow

sequenceDiagram
    autonumber

    participant API as FastAPI Router
    participant Runner as Agent Runner
    participant Fetcher as Indeed / Apify Fetcher
    participant Filter as Filter Engine
    participant Dedup as Deduplication
    participant DB as Database
    participant Extractor as Skill Extraction
    participant Scorer as Scoring
    participant Generator as Content Generator
    participant Candidate as Candidate
    participant Application as Application Agent

    API->>DB: Get CandidateProfile(id)
    DB-->>API: Return profile preferences

    API->>Runner: run_job_search_agent(profile_id, db)

    Runner->>Fetcher: fetch_indeed_jobs(roles, locations)

    Fetcher-->>Runner: Raw job listings

    loop For each raw job listing
        Runner->>Filter: evaluate_job_posting(job, candidate)

        alt Role/location/experience/salary filter fails
            Filter-->>Runner: False
            Runner->>Runner: Skip job
        else Filter passes
            Filter-->>Runner: True

            Runner->>Dedup: generate_job_id(company, title, location)
            Dedup-->>Runner: SHA-256 job_id

            Runner->>Dedup: is_duplicate_job(db, job_id)

            alt job_id already exists
                Dedup-->>Runner: Duplicate
                Runner->>Runner: Skip duplicate
            else New job
                Dedup-->>Runner: Not duplicate
                Runner->>DB: INSERT jobs

                DB-->>Extractor: Job Created Event
                Extractor->>Scorer: normalized required skills

                Scorer->>DB: INSERT score

                alt score >= 70
                    Scorer->>Generator: Content Generation Event
                    Generator->>Candidate: Generated content for approval

                    alt Candidate edits
                        Candidate->>Generator: Edited content
                        Generator->>Candidate: Updated content for approval
                    else Candidate approves
                        Candidate->>Application: Approval
                        Application->>Application: Apply to job
                    end
                else score < 70
                    Scorer->>Scorer: Stop downstream content generation
                end
            end

            alt jobs_saved >= 10
                Runner->>Runner: Stop current run
            end
        end
    end

    Runner-->>API: AgentRunSummary
    API-->>Candidate: JSON response

5. Detailed Component Breakdown

5.1 REST API & Security Layer

Modules

main.py

router/

core/security.py

core/deps.py

Responsibilities

Exposes REST endpoints for authentication, user profiles, candidate preferences, job listing queries, and triggering the Job Search Agent.

Enforces JWT authorization and password hashing.

Loads the candidate profile required by the Job Search Agent.

5.2 Job Search Agent Runner

Module

agent/runner.py

Responsibilities

Acts as the central controller for a single job-search run.

Loads candidate preferences from the database.

Coordinates Indeed/Apify fetching.

Passes raw jobs through the filtering engine.

Performs deduplication.

Persists matching, non-duplicate jobs.

Stops after saving a maximum of 10 new jobs in a run.

Does not perform in-run retries after source rate limiting.

Emits/initiates the downstream job-created event after a new job is persisted.

Run telemetry

AgentRunSummary should contain:

jobs_scanned

jobs_matched

jobs_saved

jobs_skipped_duplicate

status

5.3 Indeed / Apify Fetcher

Module

agent/indeed_fetcher.py

Responsibilities

Calls the misceres/indeed-scraper Apify Actor.

Performs searches for the candidate's configured role/location combinations.

Maps raw Apify results into the internal job schema.

Preserves nullable fields such as salary, experience, and apply link.

Stops the current run when the source is rate-limited or unavailable.

Does not retry within the same run.

5.4 Four-Criteria Filtering Engine

Modules

agent/filter.py

agent/rules/

agent/normalizers/

Role

Performs case-insensitive contiguous whole-word/phrase matching.

Example:

Candidate role:
Backend Developer

Senior Backend Developer
→ MATCH

Backend Developer Intern
→ MATCH

Backend Team Lead, Developer Relations
→ NO MATCH

The matching must not treat independently occurring words as a phrase match.

Location / Remote

A normal job must match one of the candidate's preferred locations.

If remote_opt_in = True, a job identified as remote passes regardless of the candidate's location list.

Conceptually:

role_match
AND
(remote_match OR location_match)
AND
(experience_match OR experience_missing)
AND
(salary_match OR salary_missing)

Experience

Compare the job's required experience against the candidate's configured experience range.

If experience is missing, do not exclude the job.

Salary

Normalize salary to annual INR before comparison.

Monthly salary is multiplied by 12.

If salary is missing, do not exclude the job.

6. Deduplication Subsystem

Module

agent/dedup.py

Job ID

The job_id is generated using SHA-256 from exactly:

company_name + title + location

Each value is:

lowercased

stripped of surrounding whitespace

apply_link is deliberately excluded from the hash.

Conceptually:

hash_input =
    lower(strip(company_name))
    + lower(strip(title))
    + lower(strip(location))

Then:

job_id = SHA256(hash_input)

Reason for excluding apply_link

Indeed/source URLs may contain dynamic tracking parameters. Including apply_link could cause the same job posting to receive a different hash on different fetches.

Therefore:

Same company + title + location
        ↓
Same job_id
        ↓
Duplicate detected

The database checks the jobs.job_id primary key before insertion.

7. Database Models

User

User
-------------------
id (PK)
email (Unique)
hashed_password
is_active

CandidateProfile

CandidateProfile
-------------------
id (PK)
resume_id (FK)
role_preferences (List / JSON)
preferred_locations (List / JSON)
experience_min
experience_max
salary_min
salary_max
remote_opt_in

Resume

Resume
-------------------
id (PK)
resume_file_path
extracted_skills

extracted_skills contains the candidate's normalized skills extracted from the resume once at upload time.

JobPosting

JobPosting
-------------------
job_id (PK, SHA-256)
title
company_name
location
salary_min (Nullable)
salary_max (Nullable)
experience_required_years (Nullable)
apply_link (Nullable)
platform
is_remote
description
fetched_at

8. Downstream Scoring Pipeline

The Job Search Agent's responsibility ends after a new matching job is persisted and the job-created event is emitted.

New Job
   ↓
Required Skill Extraction
   ↓
Normalized Required Skills
   ↓
Scoring
   ↓
Score persisted

The scoring component compares:

Candidate normalized skills
        VS
Job normalized required skills

The score is:

matched_required_skills
----------------------- × 100
total_required_skills

If:

score < 70

the downstream content-generation pipeline is not triggered.

If:

score >= 70

the Content Generator is triggered.

The detailed scoring rules and acceptance criteria are defined in the separate Scoring Algorithm Specification.

9. Content Generation Pipeline

When the scoring component produces a score of 70 or higher, it emits a Content Generation event.

The Content Generator produces:

Cover letter

Email

LinkedIn message

WhatsApp message

The generated content is then presented to the candidate.

The Content Generator is responsible for content generation; it does not independently decide whether the candidate should apply.

10. Candidate Approval / Edit Workflow

After content generation:

Generated Content
       ↓
Candidate Review
       │
       ├── Edit / Modify
       │       ↓
       │   Review Again
       │
       └── Approve
               ↓
        Application Agent

The candidate must approve the generated content before the Application Agent is allowed to apply.

The detailed approval state model is defined by the Approval/Application components.

11. Application Agent

The Application Agent is triggered only after explicit candidate approval.

Candidate Approval
       ↓
Application Agent
       ↓
Apply to Job

The Application Agent is responsible for interacting with the target application flow and reporting the result.

Application success/failure states are outside the Job Search Agent's responsibilities.

12. Job Search Agent Acceptance Criteria

ID

Scenario

Expected Behavior

AC1

Python Developer, Noida, 3 yrs, 9 LPA

Fetch

AC2

Python Developer, Gurgaon, 3 yrs, 9 LPA

Do not fetch

AC3

Backend Developer, Delhi, 3 yrs, 10 LPA

Fetch

AC4

Salary ₹80,000/month

Normalize to ₹9,60,000/year

AC5

Salary missing

Fetch

AC6

Experience missing

Fetch

AC7

Remote opt-in enabled + Remote job

Fetch regardless of location list

AC8

Rate-limited during run

Stop current run; no in-run retry

AC9

Job already exists by job_id

Do not insert duplicate

AC10

15 matching jobs

Save only first 10

AC11

Senior Backend Developer + role Backend Developer

Match

AC12

Backend Team Lead, Developer Relations + role Backend Developer

Do not match

AC13

Missing apply link

Fetch and store apply_link = null

AC14

Same company/title/location but different tracking URL

Same job_id; treat as duplicate

13. Event-Driven Integration

The intended downstream event flow is:

Job Search Agent
       │
       │ New Job Created
       ▼
Required Skill Extraction
       │
       ▼
Scoring Component
       │
       ├── score < 70 → END
       │
       └── score >= 70
                │
                ▼
        Content Generator
                │
                ▼
        Candidate Approval
                │
                ▼
        Application Agent

Each component owns its own responsibility.

The Job Search Agent does not:

calculate resume fit

generate content

ask the candidate for approval

apply to jobs

14. Deferred Items

The following remain intentionally deferred:

Scheduling/execution frequency.

Exact worker/queue technology for scheduled execution.

Detailed scoring implementation, covered by the Scoring Algorithm Specification.

Exact Content Generator implementation.

Exact candidate approval state model.

Exact Application Agent implementation and application-site interaction strategy.

Support for job platforms other than Indeed.

15. Design Principles

Deterministic filtering
Job Search filtering does not use an LLM.

Provider-agnostic LLM usage
Downstream LLM-powered components must not be coupled directly to a specific provider such as OpenAI or Gemini.

Separation of concerns
Fetching, filtering, deduplication, skill extraction, scoring, content generation, approval, and application are separate responsibilities.

Event-driven progression
A persisted job initiates downstream processing rather than requiring the Job Search Agent to perform scoring and content generation itself.

Human approval before application
The Application Agent cannot apply until the candidate explicitly approves the generated content.

No opportunity loss from missing optional job fields
Missing salary, experience, or apply link does not cause the Job Search Agent to discard an otherwise matching job.