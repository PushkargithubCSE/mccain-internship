import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logger import app_logger


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()

        app_logger.info(
            f"[{request_id}] "
            f"Incoming Request | "
            f"{request.method} {request.url.path}"
        )

        try:
            response = await call_next(request)

            process_time = (time.perf_counter() - start_time) * 1000

            response.headers["X-Request-ID"] = request_id

            app_logger.info(
                f"[{request_id}] "
                f"Completed | "
                f"Status={response.status_code} | "
                f"Latency={process_time:.2f} ms"
            )

            return response

        except Exception as e:
            process_time = (time.perf_counter() - start_time) * 1000

            app_logger.exception(
                f"[{request_id}] "
                f"Failed | "
                f"{type(e).__name__}: {str(e)} | "
                f"Latency={process_time:.2f} ms"
            )

            raise