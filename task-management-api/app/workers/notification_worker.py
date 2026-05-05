"""
Notification worker that consumes messages from RabbitMQ and sends emails.

Run with: python -m app.workers.notification_worker
"""

import asyncio
import json
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aio_pika
import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings
from app.core.rabbitmq import NOTIFICATION_QUEUE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

template_env = Environment(
    loader=FileSystemLoader("app/templates/email"),
    autoescape=select_autoescape(["html"]),
)


async def send_email(to_email: str, subject: str, html_body: str) -> None:
    message = MIMEMultipart("alternative")
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            use_tls=settings.SMTP_USE_TLS,
        )
        logger.info("Email sent to %s: %s", to_email, subject)
    except Exception:
        logger.error("Failed to send email to %s", to_email, exc_info=True)


async def handle_task_assigned(data: dict) -> None:
    template = template_env.get_template("task_assigned.html")
    html = template.render(**data)
    await send_email(
        to_email=data.get("assignee_email", ""),
        subject=f"Task Assigned: {data.get('task_title', '')}",
        html_body=html,
    )


async def handle_status_changed(data: dict) -> None:
    template = template_env.get_template("status_changed.html")
    html = template.render(**data)
    recipients = [
        data.get("creator_email"),
        data.get("assignee_email"),
    ]
    for email in recipients:
        if email:
            await send_email(
                to_email=email,
                subject=f"Task Status Changed: {data.get('task_title', '')}",
                html_body=html,
            )


EVENT_HANDLERS = {
    "task_assigned": handle_task_assigned,
    "task_reassigned": handle_task_assigned,
    "status_changed": handle_status_changed,
}


async def process_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
    async with message.process():
        try:
            body = json.loads(message.body.decode())
            event_type = body.get("event_type", "")
            data = body.get("data", {})

            handler = EVENT_HANDLERS.get(event_type)
            if handler:
                await handler(data)
                logger.info("Processed event: %s", event_type)
            else:
                logger.warning("Unknown event type: %s", event_type)
        except Exception:
            logger.error("Failed to process message", exc_info=True)


async def main() -> None:
    logger.info("Starting notification worker...")
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)
        queue = await channel.declare_queue(NOTIFICATION_QUEUE, durable=True)

        logger.info("Listening for notifications on queue: %s", NOTIFICATION_QUEUE)
        await queue.consume(process_message)

        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
