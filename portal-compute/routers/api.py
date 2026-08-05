from fastapi import APIRouter
from fastapi.responses import JSONResponse
from core.s3_mgr import fetch_catalog_data
from core.docker_mgr import get_workspace_metrics

router = APIRouter(prefix="/api")

@router.get("/catalog")
async def get_catalog():
    try:
        catalog_data = fetch_catalog_data()
        return JSONResponse(content={"status": "success", "data": catalog_data})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.get("/metrics/{usuario}")
async def get_metrics(usuario: str):
    try:
        metrics = get_workspace_metrics(usuario)
        if metrics.get("status") == "offline":
             return JSONResponse(content=metrics, status_code=404)
        return JSONResponse(content=metrics)
    except Exception as e:
         return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)
