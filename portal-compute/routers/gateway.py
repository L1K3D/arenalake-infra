from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid
import secrets

from core.database import get_db, engine
from core.models import User, IngestionEndpoint, Base
from core.security import get_current_user
from sqlalchemy import text

router = APIRouter(prefix="/api/admin/gateway")

class EndpointCreate(BaseModel):
    target_bucket: str
    target_filename: str
    target_format: str
    schema_definition: str

@router.get("/endpoints")
async def list_endpoints(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        return JSONResponse(content={"status": "error", "message": "Acesso negado."}, status_code=403)
    
    try:
        endpoints = db.query(IngestionEndpoint).all()
        data = []
        for e in endpoints:
            data.append({
                "id": e.id,
                "endpoint_hash": e.endpoint_hash,
                "access_token": e.access_token,
                "target_bucket": e.target_bucket,
                "target_filename": getattr(e, 'target_filename', 'dataset'), # <== NOVO
                "target_format": e.target_format,
                "schema_definition": e.schema_definition,
                "request_count": e.request_count,
                "created_at": e.created_at.strftime("%d/%m/%Y %H:%M:%S") if e.created_at else "-",
                "created_by": e.created_by
            })
        return JSONResponse(content={"status": "success", "data": data})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": f"Erro interno ao listar: {str(e)}"}, status_code=500)

@router.post("/endpoints")
async def create_endpoint(data: EndpointCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    Base.metadata.create_all(bind=engine)
    
    # HACK SEGURO: Tenta injetar a coluna nova no banco de dados antigo automaticamente
    try:
        db.execute(text("ALTER TABLE ingestion_endpoints ADD COLUMN target_filename VARCHAR DEFAULT 'dataset'"))
        db.commit()
    except:
        db.rollback() # Se der erro, a coluna já existe
        
    if current_user.role != "admin":
        return JSONResponse(content={"status": "error", "message": "Acesso negado."}, status_code=403)
    
    try:
        new_endpoint = IngestionEndpoint(
            endpoint_hash=uuid.uuid4().hex,
            access_token=secrets.token_urlsafe(32),
            target_bucket=data.target_bucket,
            target_filename=data.target_filename.replace(" ", "_"), # <== NOVO
            target_format=data.target_format,
            schema_definition=data.schema_definition,
            created_by=current_user.username
        )
        
        db.add(new_endpoint)
        db.commit()
        
        return JSONResponse(content={"status": "success", "message": "API de Ingestão criada com sucesso!"})
    except Exception as e:
        db.rollback()
        return JSONResponse(content={"status": "error", "message": f"Erro ao criar endpoint: {str(e)}"}, status_code=500)
    
@router.delete("/endpoints/{endpoint_id}")
async def delete_endpoint(endpoint_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        return JSONResponse(content={"status": "error", "message": "Acesso negado."}, status_code=403)
    
    endpoint = db.query(IngestionEndpoint).filter(IngestionEndpoint.id == endpoint_id).first()
    if not endpoint:
        return JSONResponse(content={"status": "error", "message": "Endpoint não encontrado."}, status_code=404)
    
    try:
        db.delete(endpoint)
        db.commit()
        return JSONResponse(content={"status": "success", "message": "Endpoint revogado e excluído com sucesso!"})
    except Exception as e:
        db.rollback()
        return JSONResponse(content={"status": "error", "message": f"Erro ao excluir: {str(e)}"}, status_code=500)