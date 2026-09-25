from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import JSONResponse
from core.s3_mgr import fetch_catalog_data, upload_file_to_datalake, get_file_details
from core.docker_mgr import get_workspace_metrics, update_workspace_activity
from core.security import get_current_user
from core.models import User

router = APIRouter()

@router.get("/catalog")
async def get_catalog(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's view of the MinIO data catalog."""[cite: 23]
    try:
        return JSONResponse(content={"status": "success", "data": fetch_catalog_data()})
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/metrics/{usuario}")
async def get_metrics(usuario: str, current_user: User = Depends(get_current_user)):
    """Return workspace metrics and refresh the user's activity timestamp."""[cite: 23]
    try:
        metrics = get_workspace_metrics(usuario)
        if metrics.get("status") == "offline":
            return JSONResponse(content=metrics)

        update_workspace_activity(usuario)
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/upload")
async def upload_file(
    bucket: str = Form(...), 
    usuario: str = Form(...), 
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload an authenticated user's file to the selected data lake bucket."""[cite: 23]
    try:
        upload_file_to_datalake(bucket, file.file, file.filename, usuario)
        return JSONResponse(
            content={"status": "success", "message": "Arquivo enviado com sucesso!"}
        )
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/preview/{bucket}/{filename:path}")
async def preview_file(bucket: str, filename: str, current_user: User = Depends(get_current_user)):
    """Return metadata and preview content for a stored object."""[cite: 23]
    try:
        details = get_file_details(bucket, filename)
        return JSONResponse(content={"status": "success", "data": details})
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )