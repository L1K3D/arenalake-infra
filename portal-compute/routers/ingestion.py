from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import json
import pandas as pd
import io
import boto3
import os

from core.database import get_db
from core.models import IngestionEndpoint

# Rota /api/v1/ isolada da /api/admin/ por segurança
router = APIRouter(prefix="/api/v1")

# Mapeia as credenciais buscando as variáveis mais comuns usadas em .env
minio_user = os.getenv("MINIO_ROOT_USER") or os.getenv("MINIO_ACCESS_KEY") or os.getenv("AWS_ACCESS_KEY_ID") or "admin"
minio_pass = os.getenv("MINIO_ROOT_PASSWORD") or os.getenv("MINIO_SECRET_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY") or "admin123"
minio_url = os.getenv("MINIO_ENDPOINT", "http://minio:9000")

# Instância blindada do cliente S3 (MinIO)
s3_client = boto3.client(
    's3',
    endpoint_url=minio_url,
    aws_access_key_id=minio_user,
    aws_secret_access_key=minio_pass,
    region_name="us-east-1" # Exigência do Boto3, mesmo o MinIO não usando
)

@router.get("/format/{endpoint_hash}/")
async def get_format(endpoint_hash: str, db: Session = Depends(get_db)):
    """Retorna o formato de schema esperado para o parceiro que for consumir a API"""
    endpoint = db.query(IngestionEndpoint).filter(IngestionEndpoint.endpoint_hash == endpoint_hash).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint inativo ou não encontrado.")
    
    try:
        schema = json.loads(endpoint.schema_definition)
        return JSONResponse(content={
            "status": "active",
            "endpoint_hash": endpoint_hash, 
            "target_format": endpoint.target_format,
            "expected_schema": schema,
            "instructions": "Envie um POST para a URL gerada, incluindo o Header 'Authorization: Bearer <SEU_TOKEN>'"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao processar a documentação do schema.")

@router.post("/post/{endpoint_hash}/{target_bucket}/{target_format}")
async def ingest_data(
    endpoint_hash: str, 
    target_bucket: str, 
    target_format: str, 
    request: Request,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Recebe, injeta telemetria, converte e salva os dados no MinIO"""
    
    # 1. Validação de Segurança (Bearer Token)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token Bearer ausente ou mal formatado no Header.")
    
    token = authorization.split(" ")[1]
    
    # 2. Validação contra o Banco de Dados
    endpoint = db.query(IngestionEndpoint).filter(IngestionEndpoint.endpoint_hash == endpoint_hash).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint não encontrado.")
        
    if endpoint.access_token != token:
        raise HTTPException(status_code=403, detail="Acesso Negado: Token inválido.")
        
    if endpoint.target_bucket != target_bucket or endpoint.target_format != target_format:
        raise HTTPException(status_code=400, detail="Conflito de Roteamento: O Bucket ou Formato da URL não conferem com o registro.")
        
    # 3. Leitura e Preparação do Payload
    try:
        payload = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Payload Inválido: O corpo da requisição deve ser um JSON válido.")
        
    # 4. Injeção Obrigatória do datHorRefCarga
    current_time = datetime.utcnow().isoformat()
    if isinstance(payload, dict):
        payload["datHorRefCarga"] = current_time
        data_to_save = [payload] # Empacota em lista para o Pandas processar depois
    elif isinstance(payload, list):
        for item in payload:
            item["datHorRefCarga"] = current_time
        data_to_save = payload
    else:
        raise HTTPException(status_code=400, detail="A API aceita apenas um Objeto JSON {} ou uma Lista de Objetos [{}].")

    # 5. Processamento e Escrita no Datalake (MinIO)
    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    file_key = f"api_ingestion_{endpoint_hash[:8]}_{timestamp_str}"
    
    try:
        # Garante que o bucket destino existe, se não, cria na hora
        try:
            s3_client.head_bucket(Bucket=target_bucket)
        except:
            s3_client.create_bucket(Bucket=target_bucket)

        # Roteamento de Formato
        if target_format.lower() == "json":
            file_key += ".json"
            file_content = json.dumps(data_to_save).encode('utf-8')
            s3_client.put_object(Bucket=target_bucket, Key=file_key, Body=file_content)
            
        elif target_format.lower() == "parquet":
            file_key += ".parquet"
            # O poder do Pandas entra aqui: Transforma o JSON dinamicamente num DataFrame e salva como Parquet
            df = pd.DataFrame(data_to_save)
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, index=False, engine='pyarrow')
            s3_client.put_object(Bucket=target_bucket, Key=file_key, Body=parquet_buffer.getvalue())
        else:
            raise HTTPException(status_code=400, detail="Formato corrompido.")
            
        # 6. Atualiza o Hodômetro (Count de requisições) no BD e salva
        endpoint.request_count += 1
        db.commit()
        
        return JSONResponse(status_code=201, content={
            "status": "success", 
            "message": f"Dados processados e salvos com sucesso.",
            "format": target_format.upper(),
            "records_inserted": len(data_to_save),
            "file_key": file_key
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno de I/O no DataLake: {str(e)}")