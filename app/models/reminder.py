import enum
import uuid

from sqlalchemy import Column, String, DateTime, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class ReminderStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    cancelled = "cancelled"


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Datos del destinatario
    phone_number = Column(String, nullable=False, index=True)  # formato E.164, ej: +5491122334455
    contact_name = Column(String, nullable=True)

    # Contenido del recordatorio
    message = Column(String, nullable=False)

    # Cuándo debe dispararse
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Estado del recordatorio
    status = Column(Enum(ReminderStatus), default=ReminderStatus.pending, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)
