from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from .database import Base


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