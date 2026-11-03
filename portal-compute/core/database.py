from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database URL supplied through the environment
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Verifica dinamicamente qual é o motor da base de dados
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    # Configuração específica para SQLite
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    # Configuração padrão para PostgreSQL (e outros)
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Yield a SQLAlchemy session for FastAPI dependencies.

    The session is always closed after the request finishes, including when
    the route raises an exception.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()