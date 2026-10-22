from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid
import secrets

from core.database import get_db
from core.models import User, IngestionEndpoint
from core.security import get_current_user

router = APIRouter(prefix="/api/admin/gateway")

class EndpointCreate(BaseModel):
    target_bucket: str
    target_format: str
    schema_definition: str

@router.get("/endpoints")
async def list_endpoints(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Lista todos os endpoints criados para o painel administrativo."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado.")
    
    endpoints = db.query(IngestionEndpoint).all()
    data = []
    for e in endpoints:
        data.append({
            "id": e.id,
            "endpoint_hash": e.endpoint_hash,
            "access_token": e.access_token,
            "target_bucket": e.target_bucket,
            "target_format": e.target_format,
            "schema_definition": e.schema_definition,
            "request_count": e.request_count,
            "created_at": e.created_at.strftime("%d/%m/%Y %H:%M:%S") if e.created_at else "-",
            "created_by": e.created_by
        })
        
    return JSONResponse(content={"status": "success", "data": data})

@router.post("/endpoints")
async def create_endpoint(data: EndpointCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Gera e salva um novo endpoint de ingestão criptografado."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado.")
    
    new_endpoint = IngestionEndpoint(
        endpoint_hash=uuid.uuid4().hex,
        access_token=secrets.token_urlsafe(32),
        target_bucket=data.target_bucket,
        target_format=data.target_format,
        schema_definition=data.schema_definition,
        created_by=current_user.username
    )
    
    db.add(new_endpoint)
    db.commit()
    db.refresh(new_endpoint)
    
    return JSONResponse(content={"status": "success", "message": "API de Ingestão criada com sucesso!"})