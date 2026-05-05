import json

import aio_pika
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_connection: aio_pika.abc.AbstractRobustConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None

NOTIFICATION_QUEUE = "notifications"


async def get_rabbitmq_channel() -> aio_pika.abc.AbstractChannel:
    global _connection, _channel
    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    if _channel is None or _channel.is_closed:
        _channel = await _connection.channel()
        await _channel.declare_queue(NOTIFICATION_QUEUE, durable=True)
    return _channel


async def publish_notification(event_type: str, data: dict) -> None:
    try:
        channel = await get_rabbitmq_channel()
        message = aio_pika.Message(
            body=json.dumps({"event_type": event_type, "data": data}).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await channel.default_exchange.publish(
            message,
            routing_key=NOTIFICATION_QUEUE,
        )
        logger.info("notification_published", event_type=event_type)
    except Exception:
        logger.error("notification_publish_failed", event_type=event_type, exc_info=True)


async def close_rabbitmq() -> None:
    global _connection, _channel
    if _channel and not _channel.is_closed:
        await _channel.close()
        _channel = None
    if _connection and not _connection.is_closed:
        await _connection.close()
        _connection = None
