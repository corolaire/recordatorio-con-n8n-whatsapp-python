import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.reminder import Reminder, ReminderStatus
from app.schemas.reminder import (
    ReminderCreate,
    ReminderUpdate,
    ReminderResponse,
    ReminderTriggerResponse,
)
from app.services.n8n_service import trigger_reminder_webhook, N8nWebhookError

router = APIRouter(prefix="/reminders", tags=["Reminders"])


def get_reminder_or_404(reminder_id: uuid.UUID, db: Session) -> Reminder:
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recordatorio no encontrado")
    return reminder


@router.post("/", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
def create_reminder(payload: ReminderCreate, db: Session = Depends(get_db)):
    """Crea un nuevo recordatorio."""
    reminder = Reminder(**payload.model_dump())
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.get("/", response_model=list[ReminderResponse])
def list_reminders(
    status_filter: ReminderStatus | None = None,
    active_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Lista recordatorios, con filtros opcionales por estado y activos."""
    query = db.query(Reminder)
    if status_filter:
        query = query.filter(Reminder.status == status_filter)
    if active_only:
        query = query.filter(Reminder.is_active.is_(True))
    return query.order_by(Reminder.scheduled_at).offset(skip).limit(limit).all()


@router.get("/{reminder_id}", response_model=ReminderResponse)
def get_reminder(reminder_id: uuid.UUID, db: Session = Depends(get_db)):
    """Obtiene un recordatorio por ID."""
    return get_reminder_or_404(reminder_id, db)


@router.patch("/{reminder_id}", response_model=ReminderResponse)
def update_reminder(reminder_id: uuid.UUID, payload: ReminderUpdate, db: Session = Depends(get_db)):
    """Actualiza parcialmente un recordatorio."""
    reminder = get_reminder_or_404(reminder_id, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(reminder, field, value)

    db.commit()
    db.refresh(reminder)
    return reminder


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(reminder_id: uuid.UUID, db: Session = Depends(get_db)):
    """Elimina un recordatorio."""
    reminder = get_reminder_or_404(reminder_id, db)
    db.delete(reminder)
    db.commit()
    return None


@router.post("/{reminder_id}/trigger", response_model=ReminderTriggerResponse)
async def trigger_reminder(reminder_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Dispara manualmente el envío de un recordatorio: llama al webhook
    de n8n, que se encarga de mandar el WhatsApp. Actualiza el estado
    del recordatorio según el resultado.
    """
    reminder = get_reminder_or_404(reminder_id, db)

    if not reminder.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El recordatorio está inactivo")

    try:
        response = await trigger_reminder_webhook(reminder)
    except N8nWebhookError as exc:
        reminder.status = ReminderStatus.failed
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al disparar el webhook de n8n: {exc}",
        ) from exc

    from sqlalchemy.sql import func
    reminder.status = ReminderStatus.sent
    reminder.sent_at = func.now()
    db.commit()
    db.refresh(reminder)

    return ReminderTriggerResponse(
        reminder_id=reminder.id,
        status=reminder.status,
        n8n_response_status=response.status_code,
        detail="Recordatorio enviado a n8n correctamente",
    )
