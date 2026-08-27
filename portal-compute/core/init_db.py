import os
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from .database import SessionLocal, engine, Base
from .models import User

# Contexto de criptografia segura com bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def init_db():
    # Cria as tabelas caso não existam
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    # Pega as credenciais DBA do ambiente (geradas pelo install.py)
    dba_username = os.getenv("DBA_USERNAME")
    dba_password = os.getenv("DBA_PASSWORD")

    # Verifica se o Master DBA já existe
    existing_dba = db.query(User).filter(User.username == dba_username).first()

    if not existing_dba:
        print(f"[*] Criando o Super Administrador Master: {dba_username}...")
        hashed_pw = pwd_context.hash(dba_password)

        master_dba = User(
            username=dba_username,
            hashed_password=hashed_pw,
            role="admin",
            must_change_password=False,  # O DBA Master já nasce configurado
            is_2fa_verified=True,
            full_name="System Master Administrator",
            email="admin@arenalake.internal",
            department="Infrastructure",
        )
        db.add(master_dba)
        db.commit()
        print("[+] Super Administrador criado com sucesso no banco SQLite!")
    else:
        print("[*] Super Administrador já existe no banco. Pulando criação.")

    db.close()


if __name__ == "__main__":
    init_db()