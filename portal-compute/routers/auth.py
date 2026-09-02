import pyotp
import qrcode
import base64
import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from io import BytesIO
from pydantic import BaseModel

from core.database import SessionLocal
from core.models import User
from core.security import verify_password, create_access_token, get_current_user, pwd_context

class FirstAccessSetup(BaseModel):
    new_password: str
    otp_code: str

class VerifyOtpRequest(BaseModel):
    otp_code: str

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/api/auth/login")
def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please verify your username and password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User disabled by the administrator."
        )

    # 1) First access flow: password change or 2FA not yet verified.
    if user.must_change_password or not user.is_2fa_verified:
        temp_token = create_access_token(data={"sub": user.username, "role": user.role})
        return {
            "access_token": temp_token,
            "token_type": "bearer",
            "next_step": "first_access"
        }

    # 2) Admin users are allowed to proceed after password validation.
    if user.role == "admin":
        access_token = create_access_token(data={"sub": user.username, "role": user.role})
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "next_step": "admin"
        }

    # 3) Standard users must confirm an OTP on every login.
    temp_token = create_access_token(data={"sub": user.username, "role": user.role, "scope": "otp_pending"})
    return {
        "access_token": temp_token,
        "token_type": "bearer",
        "next_step": "verify_otp"
    }


@router.get("/api/auth/2fa/generate")
def generate_2fa_qr(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate the QR code for the user's authenticator app."""
    if current_user.is_2fa_verified:
        raise HTTPException(status_code=400, detail="2FA is already configured for this user.")

    user = db.query(User).filter(User.username == current_user.username).first()

    if not user.otp_secret:
        user.otp_secret = pyotp.random_base32()
        db.commit()
        db.refresh(user)

    uri = pyotp.totp.TOTP(user.otp_secret).provisioning_uri(
        name=user.email or user.username,
        issuer_name="ArenaLake Enterprise"
    )

    qr = qrcode.make(uri)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return {"qr_code_base64": f"data:image/png;base64,{img_str}"}


@router.post("/api/auth/first-access")
def complete_first_access(data: FirstAccessSetup, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.is_2fa_verified:
        raise HTTPException(status_code=400, detail="Setup has already been completed.")

    user = db.query(User).filter(User.username == current_user.username).first()

    if not user.otp_secret:
        raise HTTPException(status_code=400, detail="2FA secret is not initialized. Refresh the page and try again.")

    totp = pyotp.TOTP(user.otp_secret)

    # Validate the OTP code using an extended verification window.
    if not totp.verify(data.otp_code, valid_window=2):
        expected = totp.now()
        import time
        server_epoch = int(time.time())
        # Debug telemetry in the browser response while onboarding is still active.
        error_msg = f"DEBUG: App sent '{data.otp_code}' | Server calculated '{expected}'. Secret: {user.otp_secret} | Epoch: {server_epoch}"
        raise HTTPException(status_code=400, detail=error_msg)

    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="The password must have at least 8 characters.")

    user.hashed_password = pwd_context.hash(data.new_password)
    user.must_change_password = False
    user.is_2fa_verified = True

    db.commit()


@router.post("/api/auth/verify-otp")
def verify_login_otp(data: VerifyOtpRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Validate the authenticator code on every standard-user login."""
    if not current_user.otp_secret:
        raise HTTPException(status_code=400, detail="2FA is not configured for this user.")

    totp = pyotp.TOTP(current_user.otp_secret)
    if not totp.verify(data.otp_code, valid_window=2):
        raise HTTPException(status_code=400, detail="Verification code (2FA) is invalid or expired.")

    # Issue the final access token when the user has validated the OTP.
    final_token = create_access_token(data={"sub": current_user.username, "role": current_user.role})

    return {
        "status": "success",
        "access_token": final_token,
        "token_type": "bearer"
    }

    return {
        "status": "success",
        "message": "Two-step authentication and the new password were configured successfully!",
        "role": user.role
    }