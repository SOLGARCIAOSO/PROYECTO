"""
app/core/database.py
Conexión a MySQL con SQLAlchemy
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,          # reconecta si la conexión cae
    pool_recycle=3600,           # recicla conexiones cada hora
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency que provee sesión de BD a cada request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
