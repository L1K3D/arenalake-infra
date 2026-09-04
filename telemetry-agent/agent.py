import os
import psutil
import distro
import platform
import subprocess
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

def ler_arquivo_sys(caminho):
    try:
        with open(caminho, 'r') as f:
            return f.read().strip()
    except Exception:
        return "Desconhecido"

def identificar_cpu():
    cpuinfo = ler_arquivo_sys("/proc/cpuinfo")
    modelo = "Desconhecido"
    for linha in cpuinfo.split("\n"):
        if "model name" in linha.lower() or "hardware" in linha.lower():
            modelo = linha.split(":")[-1].strip()
            break
    marca = "Intel" if "Intel" in modelo else "AMD" if "AMD" in modelo else "Qualcomm" if "Qualcomm" in modelo else "Exynos" if "Exynos" in modelo else "ARM/Outro"
    return marca, modelo

@app.get("/metrics")
def get_metrics():
    # Coleta de métricas da máquina local onde o agente está rodando
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    marca_cpu, modelo_cpu = identificar_cpu()
    cores_fisicos = psutil.cpu_count(logical=False) or 1
    threads = psutil.cpu_count(logical=True) or 1

    marca_pc = ler_arquivo_sys("/sys/class/dmi/id/sys_vendor")
    
    node_data = {
        "hostname": platform.node(),
        "os": f"{distro.name()} {distro.version()}",
        "marca_pc": marca_pc,
        "marca_cpu": marca_cpu,
        "modelo_cpu": modelo_cpu,
        "cores": cores_fisicos,
        "threads": threads,
        "ram_gb": round(mem.total / (1024**3), 1),
        "ram_usada_gb": round(mem.used / (1024**3), 1),
        "disk_gb": round(disk.total / (1024**3), 1),
        "disk_usado_gb": round(disk.used / (1024**3), 1),
    }
    return JSONResponse(content=node_data)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)