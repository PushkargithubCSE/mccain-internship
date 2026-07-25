from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown events.
    """

    print("Starting AI Customer Support Platform")

    # Future:
    # Initialize PostgreSQL
    # Initialize Redis
    # Initialize Qdrant

    yield

    print("Closing AI Customer Support Platform")

    # Future:
    # Close PostgreSQL
    # Close Redis
    # Close Qdrant


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(
    health_router,
    prefix=settings.API_V1_PREFIX,
)