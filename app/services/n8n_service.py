import logging
from typing import Optional

import httpx

from app.config import settings
from app.models.reminder import Reminder

logger = logging.getLogger(__name__)


class N8nWebhookError(Exception):
    """Error al comunicarse con el webhook de n8n."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)


def build_payload(reminder: Reminder) -> dict:
    """
    Arma el payload que recibe n8n. n8n lo toma y arma el mensaje
    para el nodo de WhatsApp (podés ajustar los nombres de campo
    según cómo esté mapeado tu workflow en n8n).
    """
    return {
        "reminder_id": str(reminder.id),
        "phone_number": reminder.phone_number,
        "contact_name": reminder.contact_name,
        "message": reminder.message,
        "scheduled_at": reminder.scheduled_at.isoformat(),
    }


async def trigger_reminder_webhook(reminder: Reminder) -> httpx.Response:
    """
    Envía el recordatorio al webhook de n8n vía POST (versión async, usada
    por el endpoint manual /reminders/{id}/trigger).
    n8n es responsable de tomar este payload y disparar el nodo de WhatsApp.

    Lanza N8nWebhookError si la request falla o n8n responde con error.
    """
    payload = build_payload(reminder)

    try:
        async with httpx.AsyncClient(timeout=settings.n8n_webhook_timeout) as client:
            response = await client.post(settings.n8n_webhook_url, json=payload)
    except httpx.RequestError as exc:
        logger.error(f"Error de red al llamar al webhook de n8n: {exc}")
        raise N8nWebhookError(f"No se pudo conectar con n8n: {exc}") from exc

    if response.status_code >= 400:
        logger.error(f"n8n respondió con error {response.status_code}: {response.text}")
        raise N8nWebhookError(
            f"n8n respondió con error: {response.text}",
            status_code=response.status_code,
        )

    return response


def trigger_reminder_webhook_sync(reminder: Reminder) -> httpx.Response:
    """
    Versión síncrona del trigger, usada por el scheduler interno
    (APScheduler corre el job en un thread, no en el event loop async).

    Misma lógica que la versión async: arma el payload y lo postea a n8n.
    Lanza N8nWebhookError si la request falla o n8n responde con error.
    """
    payload = build_payload(reminder)

    try:
        with httpx.Client(timeout=settings.n8n_webhook_timeout) as client:
            response = client.post(settings.n8n_webhook_url, json=payload)
    except httpx.RequestError as exc:
        logger.error(f"Error de red al llamar al webhook de n8n: {exc}")
        raise N8nWebhookError(f"No se pudo conectar con n8n: {exc}") from exc

    if response.status_code >= 400:
        logger.error(f"n8n respondió con error {response.status_code}: {response.text}")
        raise N8nWebhookError(
            f"n8n respondió con error: {response.text}",
            status_code=response.status_code,
        )

    return response
