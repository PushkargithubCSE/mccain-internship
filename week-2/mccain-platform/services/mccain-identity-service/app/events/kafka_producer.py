"""
Publishes user lifecycle events (user.registered, user.login,
user.password_changed, user.deleted) onto Kafka so other services in the
McCain platform (e.g. notifications, audit, CRM sync) can react without
being coupled to this service via REST.

Failure mode: publishing is best-effort. A Kafka outage must never break
auth flows, so publish() swallows and logs errors rather than raising.
"""
import json
from datetime import datetime, timezone
from typing import Any

import structlog
from aiokafka import AIOKafkaProducer

from app.config import settings

logger = structlog.get_logger(__name__)


class KafkaEventProducer:
    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        if not settings.KAFKA_ENABLED:
            logger.info("kafka_disabled")
            return
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            enable_idempotence=True,
            acks="all",
        )
        try:
            await self._producer.start()
            logger.info("kafka_producer_started", servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        except Exception as exc:  # pragma: no cover - infra dependent
            logger.error("kafka_producer_start_failed", error=str(exc))
            self._producer = None

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        if self._producer is None:
            logger.debug("kafka_publish_skipped_no_producer", event_type=event_type)
            return
        event = {
            "event_type": event_type,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "service": settings.APP_NAME,
            "data": payload,
        }
        try:
            await self._producer.send_and_wait(settings.KAFKA_TOPIC_USER_EVENTS, value=event, key=str(payload.get("user_id", "")).encode())
        except Exception as exc:  # pragma: no cover - infra dependent
            logger.error("kafka_publish_failed", event_type=event_type, error=str(exc))


kafka_producer = KafkaEventProducer()
