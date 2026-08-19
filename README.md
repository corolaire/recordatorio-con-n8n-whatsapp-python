# WhatsApp Reminders API

API en FastAPI para gestionar recordatorios que se envían por WhatsApp a través de un workflow de **n8n**. La API se encarga del CRUD y de disparar el webhook; **n8n es responsable de enviar el mensaje de WhatsApp** (nodo WhatsApp de n8n).

## Stack

- FastAPI
- PostgreSQL + SQLAlchemy
- httpx (cliente async para llamar al webhook de n8n)

## Arquitectura

```
Cliente → API (FastAPI) → guarda recordatorio en PostgreSQL (status: pending)

Scheduler interno (cada N segundos) → busca pending con scheduled_at vencido
                                     → Webhook n8n → Nodo WhatsApp → Mensaje enviado
                                     → actualiza status: sent / failed

(alternativa manual) POST /reminders/{id}/trigger → Webhook n8n → WhatsApp
```

La API **no envía el WhatsApp directamente**: arma el payload y lo postea al webhook de n8n. El workflow de n8n toma ese payload y lo pasa al nodo de WhatsApp.

### Scheduler interno

Corre en background (APScheduler) dentro del mismo proceso de la API. Cada `SCHEDULER_INTERVAL_SECONDS` (default 30s) revisa la tabla `reminders` buscando registros con `status=pending`, `is_active=true` y `scheduled_at <= ahora`, y los dispara automáticamente contra el webhook de n8n. Si falla, el recordatorio queda en `status=failed` (no reintenta solo).

Se puede desactivar con `SCHEDULER_ENABLED=False` en el `.env` si preferís disparar todo manualmente vía `/trigger` (por ejemplo, si preferís que sea n8n el que controle el timing con un Schedule Trigger propio).

## Instalación

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tu DATABASE_URL y N8N_WEBHOOK_URL
```

## Levantar el servidor

```bash
uvicorn app.main:app --reload
```

La documentación interactiva queda disponible en `http://localhost:8000/docs`.

## Endpoints

| Método | Endpoint                       | Descripción                                    |
|--------|---------------------------------|-------------------------------------------------|
| POST   | `/reminders/`                   | Crea un recordatorio                             |
| GET    | `/reminders/`                   | Lista recordatorios (filtros: `status_filter`, `active_only`) |
| GET    | `/reminders/{id}`                | Obtiene un recordatorio por ID                   |
| PATCH  | `/reminders/{id}`                | Actualiza parcialmente un recordatorio           |
| DELETE | `/reminders/{id}`                | Elimina un recordatorio                          |
| POST   | `/reminders/{id}/trigger`        | Dispara el envío vía webhook a n8n               |

### Ejemplo — crear recordatorio

```bash
curl -X POST http://localhost:8000/reminders/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+5491122334455",
    "contact_name": "Micky",
    "message": "No te olvides de la reunión a las 15hs",
    "scheduled_at": "2026-08-20T15:00:00-03:00"
  }'
```

### Ejemplo — disparar el recordatorio

```bash
curl -X POST http://localhost:8000/reminders/{reminder_id}/trigger
```

## Payload que recibe n8n

Cuando se dispara un recordatorio, la API postea esto al `N8N_WEBHOOK_URL`:

```json
{
  "reminder_id": "uuid",
  "phone_number": "+5491122334455",
  "contact_name": "Micky",
  "message": "No te olvides de la reunión a las 15hs",
  "scheduled_at": "2026-08-20T15:00:00-03:00"
}
```

En n8n: nodo **Webhook** (trigger) → nodo **WhatsApp** (usando esos campos para armar el mensaje).

## Posibles próximos pasos

- Autenticación con bearer token para proteger los endpoints.
- Migraciones con Alembic en vez de `create_all`.
- Reintentos automáticos para recordatorios en estado `failed`.
