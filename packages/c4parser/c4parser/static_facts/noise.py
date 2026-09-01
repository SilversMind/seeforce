# Starting allowlists — extend as real annotation runs surface more.
KNOWN_EXTERNAL_PY = {
    "stripe", "boto3", "redis", "sqlalchemy", "psycopg2", "psycopg",
    "pymongo", "kafka", "celery", "pika", "requests", "httpx",
    "django", "fastapi", "anthropic", "openai",
}

KNOWN_EXTERNAL_TS = {
    "axios", "stripe", "aws-sdk", "pg", "mongoose", "ioredis",
    "amqplib", "kafkajs", "express", "@aws-sdk",
}


def top_level_name(raw: str, language: str) -> str:
    """Return the root package/module name an import string refers to."""
    if language == "python":
        return raw.split(".")[0]
    if raw.startswith("."):
        return raw  # relative import — resolver handles it, not a package name
    parts = raw.split("/")
    if raw.startswith("@") and len(parts) >= 2:
        return "/".join(parts[:2])
    return parts[0]


def is_known_external(top_name: str, language: str) -> bool:
    if language == "python":
        return top_name in KNOWN_EXTERNAL_PY
    return top_name in KNOWN_EXTERNAL_TS
