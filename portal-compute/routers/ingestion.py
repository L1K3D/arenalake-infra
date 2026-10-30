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
from botocore.exceptions import ClientError

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
    clean_filename = endpoint.target_filename.replace(".json", "").replace(".parquet", "")
    file_key = f"{clean_filename}.{target_format.lower()}"
    
    try:
        try:
            s3_client.head_bucket(Bucket=target_bucket)
        except:
            s3_client.create_bucket(Bucket=target_bucket)

        # Baixa o arquivo existente (se houver) para fazer o Append
        file_exists = False
        existing_data = None
        try:
            response = s3_client.get_object(Bucket=target_bucket, Key=file_key)
            existing_data = response['Body'].read()
            file_exists = True
        except ClientError as e:
            if e.response['Error']['Code'] in ['NoSuchKey', '404']:
                file_exists = False
            else:
                raise

        if target_format.lower() == "json":
            if file_exists:
                existing_list = json.loads(existing_data.decode('utf-8'))
                if not isinstance(existing_list, list):
                    existing_list = [existing_list]
                existing_list.extend(data_to_save)
                final_data = existing_list
            else:
                final_data = data_to_save
                
            s3_client.put_object(Bucket=target_bucket, Key=file_key, Body=json.dumps(final_data).encode('utf-8'))
            
        elif target_format.lower() == "parquet":
            new_df = pd.DataFrame(data_to_save)
            if file_exists:
                existing_df = pd.read_parquet(io.BytesIO(existing_data))
                final_df = pd.concat([existing_df, new_df], ignore_index=True)
            else:
                final_df = new_df
                
            parquet_buffer = io.BytesIO()
            final_df.to_parquet(parquet_buffer, index=False, engine='pyarrow')
            s3_client.put_object(Bucket=target_bucket, Key=file_key, Body=parquet_buffer.getvalue())
            
        # 6. Atualiza o BD
        endpoint.request_count += 1
        db.commit()
        
        return JSONResponse(status_code=201, content={
            "status": "success", 
            "message": "Dados processados e anexados com sucesso.",
            "file": file_key,
            "records_inserted": len(data_to_save)
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro de I/O no DataLake: {str(e)}")