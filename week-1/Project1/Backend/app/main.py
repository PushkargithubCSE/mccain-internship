from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.logger import app_logger
from app.api.chat import router as chat_router

from app.core.exceptions import AppException

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown events.
    """

    print("Starting AI Customer Support Platform")
    app_logger.info("Starting AI Customer Support Platform")
    # Future:
    # Initialize PostgreSQL
    # Initialize Redis
    # Initialize Qdrant

    yield

    print("Closing AI Customer Support Platform")
    app_logger.info("Closing AI Customer Support Platform")

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
    chat_router,
    prefix=settings.API_V1_PREFIX,
)

@app.exception_handler(AppException)
async def app_exception_handler(
    request: Request,
    exc: AppException,
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_code": exc.error_code,
        },
    )