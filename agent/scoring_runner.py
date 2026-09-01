"""Scoring Algorithm orchestration helpers."""


def should_trigger_content_generator(score: int) -> bool:
    """Return whether a score meets the S6 Content Generator threshold."""
    return score >= 70


def trigger_content_generator(job_id: str) -> None:
    """
    STUB: Content Generator does not have a spec or implementation yet.
    This is intentionally a no-op placeholder so Scoring Algorithm's own
    logic (Tasks 1-4, 6-7 of scoring-algorithm-plan.md) can be built and
    verified independently, without depending on an unbuilt component.
    Replace this with a real call once Content Generator is spec'd.
    """
    import logging
    logging.getLogger(__name__).info(
        f"[STUB] Would trigger Content Generator for job_id={job_id} (score >= 70)"
    )
