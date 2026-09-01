# Scoring Algorithm — Specification

## 1. Problem Statement
Candidates manually read each job posting and compare it against their own resume to judge fit — time-consuming across many postings per day. This component automates that comparison by producing a numeric fit score for each fetched job, based on required-skills overlap with the candidate's resume.

## 2. Scope

### In Scope
- Triggered automatically when Job Search Agent writes a new matching job to the `jobs` table (event-driven, per Architecture doc)
- One-time resume skill extraction: candidate's skills are extracted from their resume via LLM **once**, at upload time, and stored — not re-extracted per job
- Per-job required-skill extraction: for each fetched job posting, required skills are extracted from the job description via LLM
- Score computed as skill overlap between candidate skills and job's required skills
- If score > 70%, triggers the Content Generator component (per Architecture doc's event-driven pipeline)

### Out of Scope
- Experience years, projects, achievements, education — **not** used in scoring (skills-only matching for v1)
- Generating cover letters/emails/messages (Content Generator's job)
- Deciding whether to apply (Application Agent's job, after candidate approval)
- Fetching job postings (Job Search Agent's job)
- Candidate-facing notifications — not needed; system is event-driven, so a score > 70% triggers Content Generator directly (S6) rather than a separate notification step

## 3. Requirements

| # | Requirement |
|---|---|
| S1 | Candidate's skills are extracted from their uploaded resume via LLM **exactly once**, at resume upload time, and stored for reuse across all future job comparisons. |
| S2 | For each fetched job posting, required skills are extracted from the job description via LLM. |
| S3 | Skill matching is **case-insensitive exact string match on normalized skill names**. Normalization happens as part of LLM extraction (both for candidate skills and job required skills): known abbreviations/synonyms are mapped to one canonical form before matching — e.g., "ML" and "Machine Learning" both normalize to "Machine Learning"; "JS" and "JavaScript" both normalize to "JavaScript"; "AI" and "Artificial Intelligence" both normalize to "Artificial Intelligence". The canonical mapping list is maintained as part of the extraction prompt/config, not hardcoded per-comparison. |
| S4 | Score is computed as: `(number of matched skills / number of required skills) * 100`, expressed as a whole percentage (0–100). |
| S5 | If the job posting has no extractable required skills (none mentioned, or LLM extraction returns empty/fails), the score is **0**, and the job remains visible to the candidate (not hidden or discarded). |
| S6 | If the resulting score is **greater than 70%**, this triggers the Content Generator component for that job. |
| S7 | Scoring only considers skills — experience, projects, achievements, and education are explicitly excluded from the score calculation (Scope Out). |

## 4. Data Written to Database
Per the Architecture doc's separate-tables design, results are written to a `scores` table, linked to `jobs` via `job_id`:
- `job_id` (foreign key to `jobs`)
- `score` (integer, 0–100)
- `matched_skills` (list of skills present in both candidate and job)
- `missing_skills` (list of required skills candidate does not have)
- `scored_at` (timestamp)

*Assumption: `matched_skills`/`missing_skills` are stored, not just the raw score, since Content Generator will likely reference them later (e.g., "you have 4 of 5 required skills") — flagging this as an assumption, not a confirmed requirement, since it wasn't explicitly discussed.*

## 5. Edge Cases

| Scenario | Behavior |
|---|---|
| Job posting has no required skills mentioned | Score = 0 (S5) |
| LLM extraction fails/errors on a job description | Score = 0, treated same as "no skills found" (S5) |
| Candidate has zero extracted skills (e.g., resume parsing failed) | Score = 0 for all jobs until resume is successfully re-processed |
| Score exactly 70% (boundary) | Does **not** trigger Content Generator — threshold is "greater than 70%," not "≥70%" (per S6 wording) |
| Same skill listed multiple times in a job description | Counted once (skills are deduplicated before matching) |

## 6. Non-Goals / Constraints
- No weighting of skills by importance/frequency — every required skill counts equally, confirmed (S3, S7)
- No re-extraction of candidate skills unless resume is re-uploaded
- Normalization (S3) only covers known abbreviation/synonym pairs configured in the extraction prompt — an unlisted synonym not in that mapping is still treated as a non-match (this boundary is inherent to S3, not a separate deferral)

## 7. Acceptance Criteria

1. **Given** a candidate with extracted skills `[Python, SQL, Docker]` and a job requiring `[Python, SQL, Kubernetes, AWS]` — **the score is 50**, because 2 of 4 required skills match.
2. **Given** a candidate with skills `[Python, SQL, Docker, AWS]` and a job requiring `[Python, AWS]` — **the score is 100**, because all required skills match.
3. **Given** a job posting where the LLM extracts zero required skills — **the score is 0**, and the job is still visible to the candidate (not discarded).
4. **Given** a job posting where required skills are listed as `[Python, python, PYTHON]` — **duplicates are collapsed**, treated as one required skill for scoring purposes.
5. **Given** a candidate skill extracted as "JavaScript" and a job requiring "JS" — **this IS counted as a match**, because both normalize to the canonical form "JavaScript" during extraction (S3).
5a. **Given** a candidate skill "Machine Learning" and a job requiring "ML" — **this IS counted as a match** (S3, same normalization rule).
6. **Given** a computed score of exactly 70 — **Content Generator is NOT triggered** (S6 — strictly greater than 70).
7. **Given** a computed score of 71 — **Content Generator IS triggered.**
8. **Given** a candidate whose resume has already been processed once — **uploading additional jobs does NOT trigger a second LLM call** for the candidate's own skills; only the job's required skills are extracted per new job (S1).

---

### Open items (intentionally deferred, not forgotten)
- [ ] Exact canonical mapping list (which abbreviations/synonyms are normalized) — needs to be drafted before extraction prompt is written
- [ ] `matched_skills`/`missing_skills` storage in Section 4 was an assumption, not explicitly confirmed by candidate/product ownere