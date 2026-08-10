import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from shared.logging import logger


class RequestMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        request_id = str(uuid.uuid4())

        start_time = time.perf_counter()

        logger.info(
            f"[{request_id}] Incoming {request.method} {request.url.path}"
        )

        response = await call_next(request)

        process_time = time.perf_counter() - start_time

        logger.info(
            f"[{request_id}] Completed in {process_time:.3f}s"
        )

        response.headers["X-Request-ID"] = request_id

        return response