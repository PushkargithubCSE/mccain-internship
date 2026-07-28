from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.logger import app_logger
from app.api.chat import router as chat_router

from app.core.exceptions import AppException
from app.middleware.logging import LoggingMiddleware
from app.schemas.base import ApiResponse

from fastapi import Request
from fastapi.responses import JSONResponse

from fastapi import HTTPException

from fastapi.middleware.cors import CORSMiddleware
from app.db.database import Base
from app.db.database import engine
from app.api.user import router as user_router

from app.api.auth import router as auth_router


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

    Base.metadata.create_all(bind=engine)

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
            "message": exc.message,
            "error_code": exc.error_code,
            "data": None,
        },
    )

app.add_middleware(LoggingMiddleware)

@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None,
        },
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
):
    app_logger.exception(exc)

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal Server Error",
            "data": None,
        },
    )

    app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(user_router, prefix=settings.API_V1_PREFIX)
app.include_router(auth_router,prefix=settings.API_V1_PREFIX,)
 