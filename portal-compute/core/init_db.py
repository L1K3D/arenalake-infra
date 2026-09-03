import os
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from .database import SessionLocal, engine, Base
from .models import User

# Configure bcrypt hashing for administrator credentials.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def init_db():
    """Create the schema and ensure the master DBA account exists.

    The initial administrator credentials are read from environment variables.
    A new account is inserted only when the configured username is absent.
    """
    # Create every declared table before querying or inserting users.
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    # Read administrator credentials provided by the installation process.
    dba_username = os.getenv("DBA_USERNAME")
    dba_password = os.getenv("DBA_PASSWORD")

    # Avoid creating duplicate administrator records on repeated startups.
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