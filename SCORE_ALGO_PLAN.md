Scoring Algorithm Specification (Updated v1.1)
1. Problem Statement

Candidates manually compare each job posting against their resume to decide whether it's worth applying. This component automates that comparison by measuring how well a candidate's skills match a job's required skills, producing a numeric fit score that drives the next stage of the application workflow.

2. Scope
In Scope

Triggered automatically whenever the Job Search Agent writes a new job to the jobs table (event-driven).

Candidate skills are extracted once from the uploaded resume using an LLM and stored for future reuse.

Required skills are extracted from each fetched job description using an LLM.

Skills are normalized to canonical names during extraction.

Generate a score based only on required-skill overlap.

Trigger the Content Generator when the score is greater than or equal to 70%.

Out of Scope

Experience, education, projects, certifications, or achievements are not part of scoring.

Generating cover letters, emails, or messages.

Applying to jobs.

Fetching job postings.

Candidate notifications.

3. Requirements

ID

	

Requirement




S1

	

Candidate skills are extracted from the uploaded resume exactly once using an LLM at resume upload time and stored in the database.




S2

	

For every newly fetched job, required skills are extracted from the job description using an LLM.




S3

	

Skill matching uses case-insensitive exact matching on normalized canonical skill names. Normalization happens during extraction, not during scoring.




S4

	

Score is calculated as: (matched required skills ÷ total required skills) × 100, rounded to a whole percentage.




S5

	

If no required skills can be extracted, the score is 0, and the job remains visible to the candidate.




S6

	

If the score is greater than or equal to 70%, the Content Generator component is triggered.




S7

	

Duplicate skills are removed before scoring. Each required skill contributes equally.




S8

	

The scoring component is deterministic and provider-agnostic. It receives normalized skills from the extraction layer and does not depend on a specific LLM provider (OpenAI, Gemini, local model, etc.).

4. Scoring Formula
Score=
Total Required Skills
Matched Required Skills
	​

×100

Example:

Candidate Skills

	

Job Required Skills

	

Score




Python, SQL, Docker

	

Python, SQL, AWS, Kubernetes

	

50%




Python, FastAPI, PostgreSQL

	

Python, FastAPI

	

100%




Python

	

Java, Spring

	

0%

5. Data Written to Database

Results are stored in the scores table.

Field

	

Description




job_id

	

Foreign key to jobs




candidate_profile_id

	

Candidate being scored




score

	

Integer (0–100)




matched_skills

	

Skills present in both candidate and job




missing_skills

	

Required skills the candidate lacks




scored_at

	

Timestamp

6. Workflow
Resume Uploaded
        │
        ▼
LLM extracts candidate skills (once)
        │
        ▼
Candidate Skills Database

New Job Saved
        │
        ▼
LLM extracts required skills
        │
        ▼
Score Calculation
        │
   ┌────┴────┐
   │         │
 <70      >=70
   │         │
 Stop   Trigger Content Generator
7. Edge Cases

Scenario

	

Behavior




Job has no required skills

	

Score = 0




Skill extraction fails

	

Score = 0




Candidate has no stored skills

	

Score = 0




Duplicate required skills

	

Count once




Score = 69

	

Do not trigger Content Generator




Score = 70

	

Trigger Content Generator




Score = 100

	

Trigger Content Generator

8. Non-Goals / Constraints

No weighted scoring.

No semantic or fuzzy matching during scoring.

No re-extraction of candidate skills unless the resume is uploaded again.

Scoring operates only on already-normalized skills.

9. Acceptance Criteria

Assume candidate skills are already extracted and stored.

#

	

Given

	

Expected




AC1

	

Candidate: Python, SQL, Docker; Job: Python, SQL, AWS, Kubernetes

	

Score = 50%




AC2

	

Candidate: Python, FastAPI, Docker, AWS; Job: Python, AWS

	

Score = 100%




AC3

	

Job has no extractable skills

	

Score = 0%




AC4

	

Job skills: Python, python, PYTHON

	

Treated as one skill




AC5

	

Candidate: JavaScript; Job: JS

	

Match after normalization




AC6

	

Candidate: Machine Learning; Job: ML

	

Match after normalization




AC7

	

Score = 69%

	

Content Generator is not triggered




AC8

	

Score = 70%

	

Content Generator is triggered




AC9

	

Resume already processed

	

Candidate skills are not extracted again

10. Event Contract

When the score is ≥ 70%, the scoring component emits a content-generation event containing:

job_id

candidate_profile_id

score

matched_skills

missing_skills

The scoring component's responsibility ends after persisting the score and emitting this event.