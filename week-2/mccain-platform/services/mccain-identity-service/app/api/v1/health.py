from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import redis_dependency
from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness():
    """Process is up. No dependency checks — used by orchestrators to detect deadlocks/crashes."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db), redis: Redis = Depends(redis_dependency)):
    """Dependencies are reachable — used to gate traffic (e.g. k8s readiness probe)."""
    checks = {"postgres": False, "redis": False}

    try:
        await db.execute(text("SELECT 1"))
        checks["postgres"] = True
    except Exception:
        pass

    try:
        await redis.ping()
        checks["redis"] = True
    except Exception:
        pass

    healthy = all(checks.values())
    return {"status": "ready" if healthy else "degraded", "checks": checks}


@router.get("/health")
async def health():
    return {"status": "ok"}
