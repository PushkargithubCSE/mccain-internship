from datetime import UTC, datetime
from uuid import uuid4


def generate_uuid() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)