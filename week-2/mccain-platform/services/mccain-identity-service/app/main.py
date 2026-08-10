import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, health, users
from app.config import settings
from app.events.kafka_producer import kafka_producer
from app.grpc_server.server import serve_grpc
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.redis_client import close_redis, get_redis

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger(__name__)

_grpc_server = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    redis = get_redis()
    await redis.ping()
    logger.info("redis_connected")

    await kafka_producer.start()

    global _grpc_server
    if settings.GRPC_ENABLED:
        _grpc_server = await serve_grpc(settings.GRPC_PORT)

    yield

    # --- Shutdown ---
    if _grpc_server is not None:
        await _grpc_server.stop(grace=5)
    await kafka_producer.stop()
    await close_redis()
    logger.info("shutdown_complete")


app = FastAPI(
    title="McCain Identity Service",
    description="Central identity & auth microservice: registration, login, JWT issuance/refresh, "
    "Redis-backed rate limiting, and internal gRPC token verification for the McCain distributed platform.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENV != "production" else None,
    redoc_url="/redoc" if settings.ENV != "production" else None,
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production to known McCain platform origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


app.include_router(health.router)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    return {"service": settings.APP_NAME, "status": "running", "version": "1.0.0"}
