import os
import boto3
from botocore.client import Config
import pandas as pd
import io

# Puxa as credenciais injetadas de forma invisível pelo Docker (nada de senha no código!)
USER_MINIO = os.environ.get('MINIO_ACCESS_KEY')
PASS_MINIO = os.environ.get('MINIO_SECRET_KEY')

print("Iniciando a leitura do MinIO com Boto3 Nativo (Credenciais Seguras)...\n")

try:
    s3_client = boto3.client(
        's3',
        endpoint_url='http://minio:9000',
        aws_access_key_id=USER_MINIO,
        aws_secret_access_key=PASS_MINIO,
        region_name='us-east-1',
        config=Config(signature_version='s3v4')
    )
    
    print("Conectado ao MinIO! Baixando o arquivo para a memória...")
    
    resposta = s3_client.get_object(Bucket='bronze', Key='MOCK_DATA.csv')
    conteudo_arquivo = resposta['Body'].read()
    df = pd.read_csv(io.BytesIO(conteudo_arquivo))
    
    print("\n✅ Leitura concluída com sucesso! Aqui estão as 5 primeiras linhas:\n")
    print(df.head())
    
    print("\n✅ Resumo do Dataset (Info):")
    df.info()

except Exception as e:
    print(f"❌ Erro ao conectar ou ler o arquivo: {e}")