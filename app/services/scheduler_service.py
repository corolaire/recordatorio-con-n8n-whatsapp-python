import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.sql import func

from app.config import settings
from app.database import SessionLocal
from app.models.reminder import Reminder, ReminderStatus
from app.services.n8n_service import trigger_reminder_webhook_sync, N8nWebhookError

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def check_and_send_pending_reminders() -> None:
    """
    Job del scheduler: busca recordatorios activos, en estado 'pending'
    y con scheduled_at ya cumplido, y los dispara vía webhook a n8n.

    Se ejecuta cada `settings.scheduler_interval_seconds`.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        due_reminders = (
            db.query(Reminder)
            .filter(
                Reminder.status == ReminderStatus.pending,
                Reminder.is_active.is_(True),
                Reminder.scheduled_at <= now,
            )
            .all()
        )

        if not due_reminders:
            return

        logger.info(f"Scheduler: {len(due_reminders)} recordatorio(s) pendiente(s) para disparar")

        for reminder in due_reminders:
            try:
                trigger_reminder_webhook_sync(reminder)
                reminder.status = ReminderStatus.sent
                reminder.sent_at = func.now()
                logger.info(f"Recordatorio {reminder.id} enviado correctamente")
            except N8nWebhookError as exc:
                reminder.status = ReminderStatus.failed
                logger.error(f"Recordatorio {reminder.id} falló al enviarse: {exc}")

            # Commit por cada recordatorio, para que un fallo en uno
            # no afecte el procesamiento de los demás.
            db.commit()

    finally:
        db.close()


def start_scheduler() -> None:
    """Arranca el scheduler si está habilitado por configuración."""
    if not settings.scheduler_enabled:
        logger.info("Scheduler deshabilitado por configuración (SCHEDULER_ENABLED=False)")
        return

    scheduler.add_job(
        check_and_send_pending_reminders,
        trigger="interval",
        seconds=settings.scheduler_interval_seconds,
        id="check_and_send_pending_reminders",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler iniciado (revisa cada {settings.scheduler_interval_seconds}s)")


def shutdown_scheduler() -> None:
    """Apaga el scheduler de forma prolija al cerrar la app."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler detenido")
