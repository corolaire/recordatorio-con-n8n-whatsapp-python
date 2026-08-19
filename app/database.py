from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency de FastAPI: abre una sesión de DB por request
    y la cierra automáticamente al terminar.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
