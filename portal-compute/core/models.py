from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime
from .database import Base
import uuid
import secrets
from datetime import datetime


class User(Base):
    """SQLAlchemy model representing a portal user and their security state."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Role used by the application for role-based access control.
    role = Column(String, default="common", nullable=False)

    # Flags controlling account activation and mandatory first-access setup.
    must_change_password = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Optional profile and organizational fields collected during onboarding.
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    department = Column(String, nullable=True)
    job_title = Column(String, nullable=True)

    # Temporary and persistent values used by the 2FA flow.
    otp_code = Column(String, nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    is_2fa_verified = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    otp_secret = Column(String, nullable=True)
    
class IngestionEndpoint(Base):
    __tablename__ = "ingestion_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    endpoint_hash = Column(String, unique=True, index=True, default=lambda: uuid.uuid4().hex)
    access_token = Column(String, unique=True, default=lambda: secrets.token_urlsafe(32))
    target_bucket = Column(String, nullable=False)
    target_filename = Column(String, nullable=False, default="dataset")
    target_format = Column(String, nullable=False) # 'json' ou 'parquet'
    schema_definition = Column(Text, nullable=True) # Regras/Tipos dos campos em formato JSON (String)
    request_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, nullable=False)