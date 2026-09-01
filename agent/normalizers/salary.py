"""
Salary Normalization & Text Parsing utilities.
Converts raw salary strings into yearly integer ranges.
"""

import re


def normalize_salary(
    amount: float | int | None,
    period: str = "yearly",
) -> int | None:
    """
    Normalizes salary amount to yearly integer.
    If period is 'monthly', multiplies by 12 (R7).
    """
    if amount is None:
        return None

    val = float(amount)
    if period.lower() in ("monthly", "month", "mo"):
        val *= 12
    return int(round(val))


def parse_salary_string(salary_str: str) -> tuple[int | None, int | None]:
    """
    Helper to parse salary strings like '₹80,000/month', '6-12 LPA', '10 LPA'.
    Returns (salary_min_yearly, salary_max_yearly).
    """
    if not salary_str:
        return None, None

    cleaned = salary_str.lower().strip().replace(",", "")

    is_monthly = "month" in cleaned or "/mo" in cleaned
    is_lpa = "lpa" in cleaned or "lac" in cleaned or "lakh" in cleaned

    numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", cleaned)]

    if not numbers:
        return None, None

    if is_lpa:
        numbers = [n * 100_000 for n in numbers]

    if is_monthly:
        numbers = [n * 12 for n in numbers]

    if len(numbers) == 1:
        val = int(round(numbers[0]))
        return val, val
    else:
        min_val = int(round(min(numbers)))
        max_val = int(round(max(numbers)))
        return min_val, max_val
