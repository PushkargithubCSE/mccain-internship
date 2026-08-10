"""
gRPC server exposing internal-only endpoints for other McCain platform
microservices: VerifyToken (hot path — every downstream authenticated
request) and GetUser (lookup by id). Runs in the same process as the
FastAPI app, on a separate port, using grpc.aio so it shares the asyncio
event loop.
"""
import uuid

import grpc
import structlog
from jose import JWTError
from sqlalchemy import select

from app.core.security import TokenType, decode_token
from app.database import AsyncSessionLocal
from app.grpc_server import identity_pb2, identity_pb2_grpc
from app.models.user import User
from app.redis_client import get_redis

logger = structlog.get_logger(__name__)


class IdentityServiceServicer(identity_pb2_grpc.IdentityServiceServicer):
    async def VerifyToken(self, request, context):
        try:
            payload = decode_token(request.access_token)
        except JWTError as exc:
            return identity_pb2.VerifyTokenResponse(valid=False, error=str(exc))

        if payload.get("type") != TokenType.ACCESS.value:
            return identity_pb2.VerifyTokenResponse(valid=False, error="not an access token")

        jti = payload.get("jti")
        if jti:
            redis = get_redis()
            if await redis.sismember("blacklist:access_tokens", jti):
                return identity_pb2.VerifyTokenResponse(valid=False, error="token revoked")

        return identity_pb2.VerifyTokenResponse(
            valid=True,
            user_id=payload.get("sub", ""),
            role=payload.get("role", ""),
        )

    async def GetUser(self, request, context):
        try:
            user_uuid = uuid.UUID(request.user_id)
        except ValueError:
            return identity_pb2.GetUserResponse(found=False)

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == user_uuid))
            user = result.scalar_one_or_none()

        if user is None:
            return identity_pb2.GetUserResponse(found=False)

        return identity_pb2.GetUserResponse(
            found=True,
            user_id=str(user.id),
            email=user.email,
            role=user.role.value,
            is_active=user.is_active,
        )


async def serve_grpc(port: int) -> grpc.aio.Server:
    server = grpc.aio.server()
    identity_pb2_grpc.add_IdentityServiceServicer_to_server(IdentityServiceServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    logger.info("grpc_server_started", port=port)
    return server
