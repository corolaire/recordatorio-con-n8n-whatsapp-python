from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Variables de entorno de la aplicación.
    Se cargan automáticamente desde un archivo .env en la raíz del proyecto.
    """

    # PostgreSQL
    database_url: str = "postgresql://user:password@localhost:5432/reminders_db"

    # n8n
    n8n_webhook_url: str = "https://your-n8n-instance.com/webhook/reminders"
    n8n_webhook_timeout: int = 10  # segundos

    # Scheduler interno
    scheduler_enabled: bool = True
    scheduler_interval_seconds: int = 30  # cada cuánto revisa recordatorios pendientes

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
