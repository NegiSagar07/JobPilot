Job Search Agent — Specification
1. Problem Statement
Candidates manually search and filter job postings across multiple platforms, checking each listing against their role, location, salary, and experience preferences before even reading the description. This is repetitive and time-consuming when done across many platforms and many listings.
This agent automates the filtering step — it does not judge job quality or fit; it only replicates the manual pre-filter a candidate does before reading a job description.
2. Scope
In Scope
Search and fetch jobs from Indeed only (v1)
Filter jobs on exactly 4 criteria: role, location, experience, salary
Optional remote opt-in as a 5th, independent filter toggle
Write matching jobs to the database
Jobs fetched via the Apify `misceres/indeed-scraper` Actor, not an official Indeed job-search API
Out of Scope
Scoring/ranking how well a job fits the candidate's resume (separate component)
Generating cover letters, emails, or LinkedIn messages (separate component)
Applying to jobs (separate component)
Platforms other than Indeed (deferred to future version)
Run frequency / scheduling mechanism (deferred — to be decided after research)
Deduplication key/mechanism (deferred — logic TBD, requirement itself is in scope)
3. Requirements
#
Requirement
R1
Candidate provides a role list (e.g., [Backend Developer, Python Developer]), either derived from their resume or manually entered/edited.
R2
Candidate provides a location list (e.g., [Delhi, Noida]).
R3
Candidate provides an experience range in years (e.g., 2–4).
R4
Candidate provides a salary range, annual (e.g., 6–12 LPA).
R5
Candidate can optionally opt in to remote jobs, independent of the location list.
R6
Agent fetches a job only if role, location, experience, AND salary all match (strict AND — no partial matches).
R7
If a job's salary is listed monthly, the agent converts it to yearly before comparing against the candidate's range.
R8
If a job posting is missing salary, the agent fetches it anyway (does not exclude on missing salary).
R9
If a job posting is missing experience, the agent fetches it anyway (candidate approves/rejects later, so no opportunity is lost by fetching).
R9a: If a job posting is missing an apply link, the agent fetches it anyway, storing apply_link as null. Loss of an opportunity is avoided the same way as missing salary (R8) and missing experience (R9).
R10
Agent does not re-fetch a job it has already fetched previously (exact matching mechanism deferred).
R11
Agent's responsibility ends once a matching job is written to the database — scoring happens elsewhere.
R12
The agent saves a maximum of 10 new jobs per run. Once 10 jobs are saved in a single run, the agent stops processing further listings for that run, even if more matching jobs remain.
R13
The job_id hash is generated from company_name + title + location only (lowercased, stripped). apply_link is deliberately EXCLUDED from the hash, because source URLs may contain dynamic tracking parameters that change between fetches of the same posting — including it would cause false negatives in duplicate detection (the same job treated as new on every run).
R14
A job title matches a candidate's role list if it contains the candidate's role string as a whole word/phrase match, case-insensitive (not a bare substring match — e.g., "Backend Developer" should match "Senior Backend Developer" but should NOT match "Backend Team Lead - Developer Relations" just because both words appear separately).

4. Data Written to Database
For each fetched job:
Job title
Company name
Location
Salary (normalized to yearly, if listed)
Experience required (if listed)
Apply link
into:
Apply link (nullable — see R9a)
Platform source (Indeed)
Fetched timestamp
Dedup key: job_id, generated as a SHA-256 hash of company_name + title + location (lowercased, stripped). apply_link is deliberately excluded to prevent false negatives caused by dynamic tracking parameters.

5. Edge Cases
Scenario
Behavior
No jobs match all filters in a run
Agent takes no action; waits for next scheduled run
Apify/Indeed rate-limits the agent
Agent stops for that run; resumes at next scheduled run (no in-run retry)
Job posting missing salary
Fetched anyway (R8)
Job posting missing experience
Fetched anyway (R9)
Job matches 3 of 4 criteria (e.g., role, experience, salary match but location doesn't)
Not fetched — all 4 criteria are required (see R6, and Acceptance Criteria below)
Candidate has opted into remote jobs
Remote jobs fetched regardless of location list match
More than 10 jobs match in a single run
Agent saves only the first 10 matching jobs and stops processing remaining listings for that run (R12)
Source apply URL contains dynamic tracking parameters
apply_link is excluded from hash calculation; job_id remains stable across fetches (R13)
Job title contains role keywords non-contiguously (e.g., "Backend Team Lead, Developer Relations")
Not fetched — role matching requires a contiguous whole word/phrase match (R14)
Job posting missing apply link -> Fetched anyway, apply_link stored as null (R9a)

6. Non-Goals / Constraints
Run frequency (hourly / continuous / fixed windows) is undecided — deferred to future research
No retry logic within a rate-limited run
No fit-scoring logic lives in this agent

7. Acceptance Criteria
Candidate filters used in examples below: role: [Backend Developer, Python Developer], location: [Delhi, Noida], experience: 2–4 years, salary: 6–12 LPA
Given a job posting "Python Developer, Noida, 3 years exp, 9 LPA" — the agent fetches it, because all 4 criteria match.
Given a job posting "Python Developer, Gurgaon, 3 years exp, 9 LPA" — the agent does NOT fetch it, because location (Gurgaon) is not in the candidate's list, even though role, experience, and salary match.
Given a job posting "Backend Developer, Delhi, 3 years exp, 10 LPA" — the agent fetches it, because all 4 criteria match.
Given a job posting salary listed as "₹80,000/month" — the agent converts it to ₹9,60,000/year before comparing against the candidate's 6–12 LPA range, and fetches it (within range).
Given a job posting "Backend Developer, Delhi, salary not listed" — the agent fetches it, per R8 (missing salary does not exclude).
Given a job posting "Backend Developer, Delhi, 9 LPA, experience not listed" — the agent fetches it, per R9 (missing experience does not exclude).
Given the candidate has opted into remote jobs, and a job posting is "Python Developer, Remote, 3 years exp, 9 LPA" — the agent fetches it, even though "Remote" is not in the candidate's location list.
Given no job postings on a run match all criteria — the agent writes nothing to the database and takes no further action until the next run.
Given Apify/Indeed returns a rate-limit response mid-run — the agent stops processing for that run without retrying, and resumes on the next scheduled run.
Given a job the agent already fetched in a previous run appears again — the agent does not write a duplicate entry (exact detection logic TBD, but no duplicate row is the expected outcome).
Given 15 job postings all match the candidate's 4 criteria in a single run — the agent saves only the first 10 and stops processing the remaining 5.
Given candidate role list [Backend Developer] and a job titled "Senior Backend Developer" — the agent treats this as a role match. Given a job titled "Backend Team Lead, Developer Relations" — the agent does NOT treat this as a role match, since "Backend Developer" does not appear as a contiguous phrase.

Open items (intentionally deferred, not forgotten)
[ ] Run frequency / scheduling
