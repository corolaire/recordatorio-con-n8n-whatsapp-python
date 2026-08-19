import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.models.reminder import ReminderStatus


class ReminderBase(BaseModel):
    phone_number: str = Field(
        ..., description="Número en formato E.164, ej: +5491122334455", examples=["+5491122334455"]
    )
    contact_name: Optional[str] = Field(None, description="Nombre del contacto (opcional)")
    message: str = Field(..., min_length=1, max_length=1000, description="Texto del recordatorio")
    scheduled_at: datetime = Field(..., description="Fecha y hora en que debe dispararse el recordatorio")


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    """Todos los campos opcionales: se actualiza solo lo que se envía."""
    phone_number: Optional[str] = None
    contact_name: Optional[str] = None
    message: Optional[str] = Field(None, min_length=1, max_length=1000)
    scheduled_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class ReminderResponse(ReminderBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ReminderStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime
    sent_at: Optional[datetime] = None


class ReminderTriggerResponse(BaseModel):
    """Respuesta al disparar manualmente un recordatorio hacia n8n."""
    reminder_id: uuid.UUID
    status: ReminderStatus
    n8n_response_status: Optional[int] = None
    detail: str
