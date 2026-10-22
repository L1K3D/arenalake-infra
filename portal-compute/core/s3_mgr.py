import os
import boto3
import pandas as pd
import io
import json
import base64
import pyarrow.parquet as pq


def get_s3_client():
    """Create a boto3 client configured for the internal MinIO endpoint."""
    minio_ak = os.environ.get("MINIO_ACCESS_KEY")
    minio_sk = os.environ.get("MINIO_SECRET_KEY")

    if not minio_ak or not minio_sk:
        raise ValueError(
            "ERRO CRÍTICO: Credenciais do MinIO (MINIO_ACCESS_KEY e MINIO_SECRET_KEY) não encontradas no ambiente!"
        )

    return boto3.client(
        "s3",
        endpoint_url="http://minio:9000",
        aws_access_key_id=minio_ak,
        aws_secret_access_key=minio_sk,
        region_name="us-east-1",
    )


def fetch_catalog_data():
    """Return a bucket-to-file mapping for objects visible in MinIO."""
    s3_client = get_s3_client()
    buckets_response = s3_client.list_buckets()
    buckets = [bucket["Name"] for bucket in buckets_response.get("Buckets", [])]

    catalog_data = {}
    for bucket in buckets:
        objects_response = s3_client.list_objects_v2(Bucket=bucket)
        contents = objects_response.get("Contents", [])

        files_structured = []
        for obj in contents:
            key = obj["Key"]

            if "_SUCCESS" in key or key.endswith(".crc") or "/_SUCCESS" in key:
                continue

            files_structured.append(key)

        catalog_data[bucket] = files_structured

    return catalog_data


def upload_file_to_datalake(bucket: str, file_obj, filename: str, username: str):
    """Upload a file to a bucket and record the uploader as object metadata."""
    s3_client = get_s3_client()
    s3_client.upload_fileobj(
        Fileobj=file_obj,
        Bucket=bucket,
        Key=filename,
        ExtraArgs={"Metadata": {"uploader": username}},
    )
    return True


def format_size(size_bytes):
    """Format a byte count using a compact B, KB, MB, or GB representation."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{round(size_bytes/1024, 2)} KB"
    elif size_bytes < 1024**3:
        return f"{round(size_bytes/(1024**2), 2)} MB"
    else:
        return f"{round(size_bytes/(1024**3), 2)} GB"


def get_file_details(bucket: str, filename: str):
    """Collect object metadata and generate a UI preview for supported formats."""
    s3_client = get_s3_client()

    if filename.endswith("_SUCCESS"):
        return {
            "filename": filename,
            "size": "0 B",
            "last_modified": "-",
            "uploader": "Apache Spark",
            "type": "info",
            "total_rows": "-",
            "total_cols": "-",
            "preview_content": "<p style='color: #8b949e; text-align: center; margin-top: 20px;'><em>Metadado do Apache Spark.</em></p>",
        }

    head = s3_client.head_object(Bucket=bucket, Key=filename)
    size_formatted = format_size(head["ContentLength"])
    last_modified = head["LastModified"].strftime("%d/%m/%Y %H:%M:%S")
    uploader = head.get("Metadata", {}).get("uploader", "Desconhecido")

    details = {
        "filename": filename,
        "size": size_formatted,
        "last_modified": last_modified,
        "uploader": uploader,
        "type": "unknown",
        "total_rows": "-",
        "total_cols": "-",
        "preview_content": "Pré-visualização não disponível.",
    }

    try:
        ext = filename.split(".")[-1].lower()
        if ext in ["png", "jpg", "jpeg"]:
            # CORREÇÃO 1: Baixa a imagem e converte para base64 para evitar bloqueios de CORS/Rede do Docker
            obj = s3_client.get_object(Bucket=bucket, Key=filename)
            img_data = obj["Body"].read()
            b64_img = base64.b64encode(img_data).decode("utf-8")
            mime_type = f"image/{ext}" if ext != "jpg" else "image/jpeg"
            
            details["type"] = "image"
            details["preview_content"] = f"data:{mime_type};base64,{b64_img}"

        elif ext == "json":
            obj = s3_client.get_object(Bucket=bucket, Key=filename)
            body = obj["Body"].read().decode("utf-8")
            try:
                parsed = json.loads(body)
                pretty_json = json.dumps(parsed, indent=4)
                details["preview_content"] = f"<pre class='preview-txt'>{pretty_json}</pre>"
            except:
                details["preview_content"] = f"<pre class='preview-txt'>{body}</pre>"
            details["type"] = "json"

        elif ext == "csv":
            # CORREÇÃO 2: Lê em stream (sem sobrecarregar a memória) para contar todas as linhas 
            # e captura apenas as primeiras 15 para desenhar a tabela.
            obj = s3_client.get_object(Bucket=bucket, Key=filename)
            head_lines = []
            total_lines = 0
            
            for line in obj["Body"].iter_lines():
                if total_lines < 15:
                    head_lines.append(line)
                total_lines += 1
                
            if head_lines:
                head_bytes = b'\n'.join(head_lines)
                df = pd.read_csv(io.BytesIO(head_bytes))
                details["total_cols"] = len(df.columns)
                details["total_rows"] = f"{max(0, total_lines - 1):,}".replace(",", ".") # Remove cabeçalho
                details["preview_content"] = df.head(10).to_html(classes="preview-table", index=False)
            else:
                details["preview_content"] = "Arquivo CSV vazio."
            
            details["type"] = "table"

        elif ext == "parquet" or "part-" in filename:
            obj = s3_client.get_object(Bucket=bucket, Key=filename)
            table = pq.read_table(io.BytesIO(obj["Body"].read()))
            df = table.to_pandas().head(10)
            details["type"] = "table"
            details["preview_content"] = df.to_html(classes="preview-table", index=False)
            details["total_cols"] = table.num_columns
            details["total_rows"] = f"{table.num_rows:,}".replace(",", ".")

        elif ext == "txt":
            obj = s3_client.get_object(Bucket=bucket, Key=filename)
            body = obj["Body"].read().decode("utf-8")
            details["type"] = "text"
            details["preview_content"] = f"<pre class='preview-txt'>\n".join(body.split("\n")[:10]) + "</pre>"

    except Exception as e:
        details["preview_content"] = f"Erro ao gerar sample: {str(e)}"

    return details


def delete_file_from_datalake(bucket: str, filename: str):
    """Delete an object from a MinIO bucket for an authorized administrator."""
    s3_client = get_s3_client()
    s3_client.delete_object(Bucket=bucket, Key=filename)
    return True


def create_bucket_in_datalake(bucket_name: str):
    """Create a new bucket in the MinIO data lake."""
    s3_client = get_s3_client()
    clean_name = bucket_name.lower().replace("_", "-").strip()
    
    try:
        s3_client.head_bucket(Bucket=clean_name)
        return False, "O bucket já existe no MinIO."
    except Exception:
        try:
            s3_client.create_bucket(Bucket=clean_name)
            return True, clean_name
        except Exception as e:
            return False, f"Erro ao criar bucket: {str(e)}"


def delete_bucket_from_datalake(bucket_name: str):
    """Exclui todos os arquivos de um bucket recursivamente e depois exclui o próprio bucket."""
    s3_client = get_s3_client()
    try:
        objects = s3_client.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in objects:
            for obj in objects['Contents']:
                s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])
                
        s3_client.delete_bucket(Bucket=bucket_name)
        return True, ""
    except Exception as e:
        
        return False, str(e)
    
def generate_catalog_report():
    """Gera um relatório consolidado com metadados e shape de todos os arquivos."""
    s3_client = get_s3_client()
    buckets_response = s3_client.list_buckets()
    buckets = [bucket["Name"] for bucket in buckets_response.get("Buckets", [])]

    report_data = []

    for bucket in buckets:
        objects_response = s3_client.list_objects_v2(Bucket=bucket)
        contents = objects_response.get("Contents", [])

        for obj in contents:
            key = obj["Key"]
            
            # Ignora lixos do Spark
            if "_SUCCESS" in key or key.endswith(".crc") or "/_SUCCESS" in key:
                continue

            try:
                head = s3_client.head_object(Bucket=bucket, Key=key)
                size_formatted = format_size(head["ContentLength"])
                last_modified = head["LastModified"].strftime("%d/%m/%Y %H:%M:%S")
                uploader = head.get("Metadata", {}).get("uploader", "Desconhecido")
                
                ext = key.split(".")[-1].lower() if "." in key else "unknown"
                if "part-" in key and ext != "parquet":
                    ext = "parquet"

                total_rows = "-"
                total_cols = "-"

                # Tenta extrair shape se for dado tabular
                if ext == "csv":
                    file_obj = s3_client.get_object(Bucket=bucket, Key=key)
                    head_lines = []
                    total_lines = 0
                    for line in file_obj["Body"].iter_lines():
                        if total_lines < 2:
                            head_lines.append(line)
                        total_lines += 1
                    
                    if head_lines:
                        try:
                            df = pd.read_csv(io.BytesIO(b'\n'.join(head_lines)))
                            total_cols = str(len(df.columns))
                        except Exception:
                            total_cols = "Erro"
                        total_rows = str(max(0, total_lines - 1))
                        
                elif ext == "parquet":
                    try:
                        file_obj = s3_client.get_object(Bucket=bucket, Key=key)
                        pf = pq.ParquetFile(io.BytesIO(file_obj["Body"].read()))
                        total_cols = str(pf.metadata.num_columns)
                        total_rows = str(pf.metadata.num_rows)
                    except Exception:
                        total_cols = "Erro"
                        total_rows = "Erro"

                report_data.append({
                    "Bucket": bucket,
                    "Arquivo": key,
                    "Tipo": ext.upper(),
                    "Data_Hora": last_modified,
                    "Linhas": total_rows,
                    "Colunas": total_cols,
                    "Uploader": uploader,
                    "Tamanho": size_formatted
                })
            except Exception as e:
                print(f"Erro ao gerar relatorio para {key}: {e}")

    return report_data

def get_datalake_dashboard_metrics():
    """Calcula e consolida métricas gerenciais para o Dashboard do Data Lake."""
    s3_client = get_s3_client()
    buckets_response = s3_client.list_buckets()
    buckets = [bucket["Name"] for bucket in buckets_response.get("Buckets", [])]

    total_bytes = 0
    total_files = 0
    files_by_bucket = {}
    files_by_type = {}
    bytes_by_type = {}
    files_by_uploader = {}

    for bucket in buckets:
        files_by_bucket[bucket] = 0
        try:
            objects_response = s3_client.list_objects_v2(Bucket=bucket)
            contents = objects_response.get("Contents", [])

            for obj in contents:
                key = obj["Key"]
                if "_SUCCESS" in key or key.endswith(".crc") or "/_SUCCESS" in key:
                    continue
                    
                size = obj["Size"]
                total_bytes += size
                total_files += 1
                files_by_bucket[bucket] += 1
                
                ext = key.split(".")[-1].lower() if "." in key else "unknown"
                if "part-" in key and ext != "parquet":
                    ext = "parquet"
                
                files_by_type[ext] = files_by_type.get(ext, 0) + 1
                bytes_by_type[ext] = bytes_by_type.get(ext, 0) + size
                
                # Extrai o uploader para o ranking
                try:
                    head = s3_client.head_object(Bucket=bucket, Key=key)
                    uploader = head.get("Metadata", {}).get("uploader", "Desconhecido")
                    files_by_uploader[uploader] = files_by_uploader.get(uploader, 0) + 1
                except:
                    pass
        except Exception:
            pass

    return {
        "total_bytes_fmt": format_size(total_bytes),
        "total_files": total_files,
        "total_buckets": len(buckets),
        "files_by_bucket": files_by_bucket,
        "files_by_type": files_by_type,
        "bytes_by_type": bytes_by_type,
        "files_by_uploader": files_by_uploader
    }