# ============================================================================
# S3/MinIO Data Lake Manager
# ============================================================================
# This module handles all interactions with the MinIO object storage service.
# Provides functions for:
# - Catalog browsing: list buckets and files
# - File management: upload files with metadata
# - File preview: extract and format data for UI display
# - Connection management: handle S3 credentials securely
# ============================================================================

import os
import boto3
import pandas as pd
import io


def get_s3_client():
    """Initialize and return a boto3 S3 client configured for MinIO.
    
    Retrieves MinIO credentials from environment variables (injected via docker-compose).
    Raises ValueError if credentials are not found.
    Endpoint is configured for MinIO at http://minio:9000 (internal Docker network).
    """
    # Retrieve credentials from environment variables (set in docker-compose)
    minio_ak = os.environ.get("MINIO_ACCESS_KEY")
    minio_sk = os.environ.get("MINIO_SECRET_KEY")

    # Fail fast if credentials are missing
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
    """Fetch and structure all buckets and files from MinIO.
    
    Returns a dictionary where keys are bucket names and values are
    lists of file paths within each bucket.
    Filters out Spark metadata files (_SUCCESS, .crc) automatically.
    """
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

            # Filter out Spark metadata files (_SUCCESS files, .crc checksums, etc.)
            # These are internal Spark artifacts, not user data
            if "_SUCCESS" in key or key.endswith(".crc") or "/_SUCCESS" in key:
                continue

            files_structured.append(key)

        catalog_data[bucket] = files_structured

    return catalog_data


def upload_file_to_datalake(bucket: str, file_obj, filename: str, username: str):
    """Upload a file to MinIO with uploader metadata.
    
    Args:
        bucket: Target bucket name
        file_obj: File object to upload
        filename: Name of the file
        username: Username of the uploader (stored as metadata)
    """
    s3_client = get_s3_client()
    s3_client.upload_fileobj(
        Fileobj=file_obj,
        Bucket=bucket,
        Key=filename,
        ExtraArgs={"Metadata": {"uploader": username}},
    )
    return True


def format_size(size_bytes):
    """Convert byte count to human-readable format (B, KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{round(size_bytes/1024, 2)} KB"
    elif size_bytes < 1024**3:
        return f"{round(size_bytes/(1024**2), 2)} MB"
    else:
        return f"{round(size_bytes/(1024**3), 2)} GB"


def get_file_details(bucket: str, filename: str):
    """Fetch file metadata and generate a preview for the UI.
    
    Handles multiple file formats:
    - Images (PNG, JPG): generates presigned URL for display
    - CSV files: reads first 10 rows and returns HTML table
    - Parquet files: reads first 10 rows and returns HTML table
    - Text files: reads first 10 lines
    
    Returns a dictionary with file metadata and preview content.
    """
    s3_client = get_s3_client()

    if filename.endswith("_SUCCESS"):
        return {
            "filename": filename,
            "size": "0 B",
            "last_modified": "-",
            "uploader": "Apache Spark",
            "type": "info",
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
        "preview_content": "Pré-visualização não disponível.",
    }

    try:
        ext = filename.split(".")[-1].lower()
        if ext in ["png", "jpg", "jpeg"]:
            url = s3_client.generate_presigned_url(
                "get_object", Params={"Bucket": bucket, "Key": filename}, ExpiresIn=3600
            )
            details["type"] = "image"
            details["preview_content"] = url.replace(
                "http://minio:9000", "http://localhost:9000"
            )

        elif ext == "csv":
            obj = s3_client.get_object(Bucket=bucket, Key=filename)
            df = pd.read_csv(io.BytesIO(obj["Body"].read()), nrows=10)
            details["type"] = "table"
            details["preview_content"] = df.to_html(
                classes="preview-table", index=False
            )

        elif ext == "parquet" or "part-" in filename:
            obj = s3_client.get_object(Bucket=bucket, Key=filename)
            df = pd.read_parquet(io.BytesIO(obj["Body"].read()), engine="pyarrow")
            details["type"] = "table"
            details["preview_content"] = df.head(10).to_html(
                classes="preview-table", index=False
            )

        elif ext == "txt":
            obj = s3_client.get_object(Bucket=bucket, Key=filename)
            body = obj["Body"].read().decode("utf-8")
            details["type"] = "text"
            details["preview_content"] = "\n".join(body.split("\n")[:10])

    except Exception as e:
        details["preview_content"] = f"Erro ao gerar sample: {str(e)}"

    return details