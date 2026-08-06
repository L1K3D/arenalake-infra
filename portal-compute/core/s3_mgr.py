import boto3
import pandas as pd
import io

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url='http://minio:9000',
        aws_access_key_id='arenalake',
        aws_secret_access_key='arenalake123',
        region_name='us-east-1'
    )

def fetch_catalog_data():
    s3_client = get_s3_client()
    buckets_response = s3_client.list_buckets()
    buckets = [bucket['Name'] for bucket in buckets_response.get('Buckets', [])]

    catalog_data = {}
    for bucket in buckets:
        objects_response = s3_client.list_objects_v2(Bucket=bucket)
        files = [obj['Key'] for obj in objects_response.get('Contents', [])]
        catalog_data[bucket] = files
    return catalog_data

def upload_file_to_datalake(bucket: str, file_obj, filename: str, username: str):
    s3_client = get_s3_client()
    # Injeta o usuário como metadado no momento do upload
    s3_client.upload_fileobj(
        Fileobj=file_obj,
        Bucket=bucket,
        Key=filename,
        ExtraArgs={"Metadata": {"uploader": username}}
    )
    return True

def format_size(size_bytes):
    if size_bytes < 1024: return f"{size_bytes} B"
    elif size_bytes < 1024**2: return f"{round(size_bytes/1024, 2)} KB"
    elif size_bytes < 1024**3: return f"{round(size_bytes/(1024**2), 2)} MB"
    else: return f"{round(size_bytes/(1024**3), 2)} GB"

def get_file_details(bucket: str, filename: str):
    s3_client = get_s3_client()
    
    # 1. Pega os metadados (Tamanho, Data, Uploader)
    head = s3_client.head_object(Bucket=bucket, Key=filename)
    size_formatted = format_size(head['ContentLength'])
    last_modified = head['LastModified'].strftime("%d/%m/%Y %H:%M:%S")
    uploader = head.get('Metadata', {}).get('uploader', 'Desconhecido (Via Console MinIO)')
    
    details = {
        "filename": filename,
        "size": size_formatted,
        "last_modified": last_modified,
        "uploader": uploader,
        "type": "unknown",
        "preview_content": "Pré-visualização não disponível para este formato."
    }

    # 2. Gera a pré-visualização dependendo do arquivo
    try:
        ext = filename.split('.')[-1].lower()
        if ext in ['png', 'jpg', 'jpeg']:
            # Gera uma URL temporária (1 hora) para o navegador renderizar a imagem
            url = s3_client.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': filename}, ExpiresIn=3600)
            # TRUQUE DE MESTRE: Troca 'minio' por 'localhost' para o navegador de fora conseguir ler
            url_externa = url.replace("http://minio:9000", "http://localhost:9000")
            details["type"] = "image"
            details["preview_content"] = url_externa
            
        elif ext == 'csv':
            # Lê só as primeiras linhas na memória usando Pandas
            obj = s3_client.get_object(Bucket=bucket, Key=filename)
            body = obj['Body'].read()
            df = pd.read_csv(io.BytesIO(body), nrows=10)
            details["type"] = "table"
            details["preview_content"] = df.to_html(classes="preview-table", index=False)
            
        elif ext == 'txt':
            obj = s3_client.get_object(Bucket=bucket, Key=filename)
            body = obj['Body'].read().decode('utf-8')
            linhas = body.split('\n')[:10]
            details["type"] = "text"
            details["preview_content"] = '\n'.join(linhas)
            
    except Exception as e:
        details["preview_content"] = f"Erro ao gerar sample: {str(e)}"
        
    return details
