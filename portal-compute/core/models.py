from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Nível de Acesso (RBAC): 'admin' ou 'common'
    role = Column(String, default="common", nullable=False)

    # Trava de Segurança para Primeiro Acesso
    must_change_password = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Dados de Perfil / LGPD (Preenchidos pelo usuário comum no onboarding)
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    department = Column(String, nullable=True)
    job_title = Column(String, nullable=True)

    # Autenticação de Dois Fatores (2FA)
    otp_code = Column(String, nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    is_2fa_verified = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)