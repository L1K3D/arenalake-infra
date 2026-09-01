import pyotp
import qrcode
import base64

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
    # 1. Consulta o usuário no banco SQLite pelo username
    user = db.query(User).filter(User.username == form_data.username).first()
    
    # 2. Valida se o usuário existe e se a senha confere via bcrypt
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas. Verifique usuário e senha.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Valida se o usuário está ativo na infraestrutura
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Usuário desativado pelo Administrador."
        )

    # 4. Cria o Token JWT contendo as claims de segurança (usuário e role)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role,
        "must_change_password": user.must_change_password,
        "is_2fa_verified": user.is_2fa_verified
    }
    
@router.get("/api/auth/2fa/generate")
def generate_2fa_qr(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Gera o QR Code exclusivo para o Autenticador do usuário"""
    if current_user.is_2fa_verified:
        raise HTTPException(status_code=400, detail="2FA já está configurado para este usuário.")

    # Gera um segredo aleatório do Google Authenticator
    secret = pyotp.random_base32()
    
    # Salva usando o nome correto da coluna (otp_secret)
    current_user.otp_secret = secret
    db.commit()

    # Monta a URI que o app entende
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email or current_user.username, 
        issuer_name="ArenaLake Enterprise"
    )

    # Gera a imagem do QR Code em Base64 para o Front-end ler sem precisar baixar arquivo
    qr = qrcode.make(uri)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return {"qr_code_base64": f"data:image/png;base64,{img_str}"}

@router.post("/api/auth/first-access")
def complete_first_access(data: FirstAccessSetup, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Valida o código de 6 dígitos e salva a nova senha"""
    if current_user.is_2fa_verified:
        raise HTTPException(status_code=400, detail="Setup já foi realizado.")

    # Blindagem: se o otp_secret estiver nulo no banco, gera um novo na hora para evitar crash
    if not current_user.otp_secret:
        current_user.otp_secret = pyotp.random_base32()
        db.commit()

    # 1. Valida o código 2FA (TOTP)
    totp = pyotp.TOTP(current_user.otp_secret)
    if not totp.verify(data.otp_code, valid_window=2):
        raise HTTPException(status_code=400, detail="Código de autenticação (2FA) inválido.")

    # 2. Valida regras básicas da nova senha
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="A senha deve ter pelo menos 8 caracteres.")

    # 3. Salva a nova senha com Hash e libera o usuário
    current_user.hashed_password = pwd_context.hash(data.new_password)
    current_user.must_change_password = False
    current_user.is_2fa_verified = True
    
    db.commit()

    return {"status": "success", "message": "Autenticação em duas etapas e senha configuradas com sucesso!"}