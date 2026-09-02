import os
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from .database import SessionLocal, engine, Base
from .models import User

# Secure password hashing context using bcrypt.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def init_db():
    """Create the schema and ensure the master DBA administrator exists."""
    # Ensure all tables exist before accessing users or creating records.
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    # Retrieve the DBA credentials injected by the installation process.
    dba_username = os.getenv("DBA_USERNAME")
    dba_password = os.getenv("DBA_PASSWORD")

    # Verify whether the master DBA user already exists.
    existing_dba = db.query(User).filter(User.username == dba_username).first()

    if not existing_dba:
        print(f"[*] Creating the Master Super Administrator: {dba_username}...")
        hashed_pw = pwd_context.hash(dba_password)

        master_dba = User(
            username=dba_username,
            hashed_password=hashed_pw,
            role="admin",
            must_change_password=True,
            is_2fa_verified=False,
            full_name="System Master Administrator",
            email="admin@arenalake.internal",
            department="Infrastructure",
        )
        db.add(master_dba)
        db.commit()
        print("[+] Master Super Administrator created successfully in the SQLite database!")
    else:
        print("[*] The master super administrator already exists. Skipping creation.")

    db.close()


if __name__ == "__main__":
    init_db()