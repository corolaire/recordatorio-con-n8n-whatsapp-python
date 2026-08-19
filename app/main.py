from fastapi import FastAPI

from app.database import Base, engine
from app.models import Reminder  # noqa: F401  (necesario para que Base los registre)
from app.routers import reminders
from app.services.scheduler_service import start_scheduler, shutdown_scheduler

# Crea las tablas si no existen (para desarrollo rápido).
# En producción es preferible manejar el schema con Alembic.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WhatsApp Reminders API",
    description="API para gestionar recordatorios que se envían por WhatsApp a través de un workflow de n8n.",
    version="1.0.0",
)

app.include_router(reminders.router)


@app.on_event("startup")
def on_startup():
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    shutdown_scheduler()


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "whatsapp-reminders-api"}
