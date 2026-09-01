"""Safety-net normalization for skills returned by LLM extraction."""

CANONICAL_SKILL_MAP: dict[str, str] = {
    "python": "Python",
    "sql": "SQL",
    "docker": "Docker",
    "ml": "Machine Learning",
    "ai": "Artificial Intelligence",
    "js": "JavaScript",
    "ts": "TypeScript",
    "k8s": "Kubernetes",
    "aws": "Amazon Web Services",
    "gcp": "Google Cloud Platform",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "postgres": "PostgreSQL",
}


def normalize_skill(raw_skill: str) -> str:
    """Return a canonical skill name after LLM extraction."""
    normalized_skill = raw_skill.strip().lower()
    return CANONICAL_SKILL_MAP.get(normalized_skill, normalized_skill.title())
