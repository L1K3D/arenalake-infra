from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.models import User
from core.security import verify_password, create_access_token

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