import json
import subprocess
import httpx
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from core.database import get_db
from core.models import User
from core.docker_mgr import client as docker_client, shutdown_workspace, get_allocatable_resources
from core.s3_mgr import fetch_catalog_data, upload_file_to_datalake, delete_file_from_datalake
from core.security import get_current_user

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter()

class UserCreateRequest(BaseModel):
    username: str
    password: str
    full_name: str
    email: str
    department: str = "General"
    role: str = "common"

class DangerDestroyRequest(BaseModel):
    confirm_username: str

class SelfDeleteRequest(BaseModel):
    confirmation_phrase: str

class UserPasswordResetRequest(BaseModel):
    new_password: str


@router.get("/system/resources")
async def get_system_resources(current_user: User = Depends(get_current_user)):
    """Return CPU and memory capacity calculated from the Docker Swarm."""[cite: 23]
    data = get_allocatable_resources()
    if "error" in data:
        return JSONResponse(
            content={"status": "error", "message": data["error"]}, status_code=500
        )
    return JSONResponse(content={"status": "success", "data": data})


@router.get("/admin/users")
async def admin_list_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all registered users for authenticated administrators."""[cite: 23]
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    users = db.query(User).all()
    user_list = []
    for u in users:
        user_list.append({
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "is_2fa_verified": u.is_2fa_verified
        })
    return JSONResponse(content={"status": "success", "users": user_list})


@router.post("/admin/users")
async def admin_create_user(req: UserCreateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a user with a temporary password and selected access role."""[cite: 23]
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Nome de usuário já existe.")

    if req.role not in ["admin", "common"]:
        raise HTTPException(status_code=400, detail="Perfil inválido. Escolha entre 'admin' ou 'common'.")

    hashed_pw = pwd_context.hash(req.password)
    new_user = User(
        username=req.username.lower().strip().replace(" ", "-"),
        hashed_password=hashed_pw,
        full_name=req.full_name,
        email=req.email,
        department=req.department,
        role=req.role,
        must_change_password=True,
        is_2fa_verified=False
    )
    db.add(new_user)
    db.commit()

    return JSONResponse(content={"status": "success", "message": f"Usuário '{new_user.username}' ({req.role}) criado com sucesso!"})


@router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a standard user while protecting administrator accounts."""[cite: 23]
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    if user_to_delete.id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir sua própria conta de administrador.")
    
    if user_to_delete.role == "admin":
        raise HTTPException(status_code=400, detail="Contas de Administrador são protegidas e não podem ser excluídas por esta via.")

    db.delete(user_to_delete)
    db.commit()

    return JSONResponse(content={"status": "success", "message": f"Usuário '{user_to_delete.username}' excluído com sucesso!"})


@router.get("/admin/workspaces")
async def admin_list_workspaces(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List active user workspace services and their reserved resources."""[cite: 23]
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    if not docker_client:
        return JSONResponse(content={"status": "success", "workspaces": []})

    active_workspaces = []
    try:
        services = docker_client.services.list()
        for svc in services:
            if svc.name.startswith("vscode-"):
                username = svc.name.replace("vscode-", "")
                tasks = svc.tasks(filters={"desired-state": "running"})
                
                is_running = False
                node_id = "Desconhecido"
                for task in tasks:
                    if task["Status"]["State"] == "running":
                        is_running = True
                        node_id = task.get("NodeID", "N/A")
                        break
                
                if is_running:
                    spec = svc.attrs.get("Spec", {}).get("TaskTemplate", {}).get("Resources", {}).get("Limits", {})
                    cpu_cores = spec.get("NanoCPUs", 0) / 1e9
                    ram_mb = spec.get("MemoryBytes", 0) / (1024 * 1024)

                    active_workspaces.append({
                        "username": username,
                        "service_name": svc.name,
                        "cpu": f"{cpu_cores} Cores",
                        "ram": f"{round(ram_mb, 1)} MB",
                        "node": node_id
                    })
    except Exception as e:
        print(f"Erro ao inspecionar Docker Swarm: {e}")

    return JSONResponse(content={"status": "success", "workspaces": active_workspaces})


@router.post("/admin/workspaces/kill/{username}")
async def admin_kill_workspace(username: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Immediately remove the selected user's VS Code and Spark services."""[cite: 23]
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    try:
        shutdown_workspace(username)
        return JSONResponse(content={"status": "success", "message": f"Sessão do usuário '{username}' encerrada com sucesso pelo Kill Switch."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao encerrar sessão: {str(e)}")


@router.get("/admin/cluster/nodes")
async def admin_cluster_nodes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return Swarm node roles, readiness, CPU capacity, memory capacity, and real-time telemetry."""[cite: 23]
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    if not docker_client:
        return JSONResponse(content={"status": "success", "nodes": []})
    
    telemetry_by_node = {}
    try:
        for svc in docker_client.services.list():
            if "telemetry-agent" in svc.name:
                for task in svc.tasks(filters={"desired-state": "running"}):
                    node_id = task.get("NodeID")
                    task_ip = None
                    for network in task.get("NetworksAttachments", []):
                        for addr in network.get("Addresses", []):
                            task_ip = addr.split("/")[0]
                            break
                        if task_ip: break
                        
                    if node_id and task_ip:
                        try:
                            response = httpx.get(f"http://{task_ip}:5000/metrics", timeout=3.0)
                            if response.status_code == 200:
                                telemetry_by_node[node_id] = response.json()
                        except Exception as e:
                            print(f"Falha ao conectar na telemetria {task_ip}: {e}")
    except Exception as e:
        print(f"Erro ao orquestrar tarefas de telemetria: {e}")
        
    nodes_data = []
    try:
        nodes = docker_client.nodes.list()
        for node in nodes:
            attrs = node.attrs
            status = attrs.get("Status", {}).get("State", "unknown")
            role = attrs.get("Spec", {}).get("Role", "worker")
            labels = attrs.get("Spec", {}).get("Labels", {})
            papel = labels.get("papel", role)
            hostname = attrs.get("Description", {}).get("Hostname", "unknown")
            resources = attrs.get("Description", {}).get("Resources", {})
            total_cpus = resources.get("NanoCPUs", 0) / 1e9
            total_mem = resources.get("MemoryBytes", 0) / (1024**3)
            
            node_info = {
                "id": node.id,
                "hostname": hostname,
                "role": papel.upper(),
                "status": status,
                "cpus": round(total_cpus, 1),
                "memory_gb": round(total_mem, 1)
            }
            
            t_data = telemetry_by_node.get(node.id)
            if t_data:
                node_info["cpu_percent"] = t_data.get("cpu_percent", 0.0)
                node_info["marca_cpu"] = t_data.get("marca_cpu", "Desconhecido")
                node_info["modelo_cpu"] = t_data.get("modelo_cpu", "Desconhecido")
                node_info["disk_gb"] = t_data.get("disk_gb", 0)
                node_info["disk_usado_gb"] = t_data.get("disk_usado_gb", 0)
                
                ram_total = t_data.get("ram_gb", 1)
                ram_usada = t_data.get("ram_usada_gb", 0)
                if ram_total > 0:
                    node_info["ram_percent"] = round((ram_usada / ram_total) * 100, 1)
            
            nodes_data.append(node_info)
    except Exception as e:
        print(f"Erro ao ler nós do Swarm: {e}")
    
    return JSONResponse(content={"status": "success", "nodes": nodes_data})


@router.get("/admin/files/{username}")
async def admin_inspect_user_files(username: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Inspect a user's persistent volume through a temporary read-only container."""[cite: 23]
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    if not docker_client:
        raise HTTPException(status_code=500, detail="Cliente Docker offline.")
    
    vol_name = f"arena-vol-{username}"
    files_list = []
    try:
        output = docker_client.containers.run(
            image="alpine:latest",
            command="find /data -maxdepth 3 -not -path '*/.*'",
            volumes={vol_name: {"bind": "/data", "mode": "ro"}},
            remove=True
        )
        files_list = output.decode("utf-8").splitlines()
    except Exception as e:
        files_list = [f"Volume não encontrado ou vazio para '{username}' ({str(e)})"]
        
    return JSONResponse(content={"status": "success", "username": username, "files": files_list})


@router.post("/admin/danger/destroy")
async def admin_self_destruct(req: DangerDestroyRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Remove all active workspace and Spark Worker services after confirmation."""[cite: 23]
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    if req.confirm_username != current_user.username:
        raise HTTPException(status_code=400, detail="O nome de usuário digitado não confere com o seu usuário admin atual.")
    
    try:
        if docker_client:
            services = docker_client.services.list()
            for svc in services:
                if svc.name.startswith("vscode-") or svc.name.startswith("spark-worker-"):
                    try:
                        svc.remove()
                    except:
                        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na execução da autodestruição: {str(e)}")
        
    return JSONResponse(content={"status": "success", "message": "Protocolo de Autodestruição executado com sucesso. Todos os workspaces ativos foram purgados."})


@router.get("/admin/catalog")
async def admin_get_catalog(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the complete MinIO bucket catalog for administrator auditing."""[cite: 23]
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    try:
        return JSONResponse(content={"status": "success", "data": fetch_catalog_data()})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@router.delete("/admin/catalog/file")
async def admin_delete_catalog_file(bucket: str = Form(...), filename: str = Form(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a dataset or Parquet object from the catalog as an administrator."""[cite: 23]
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    try:
        delete_file_from_datalake(bucket, filename)
        return JSONResponse(content={"status": "success", "message": f"Arquivo '{filename}' removido do bucket '{bucket}' com sucesso!"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao excluir arquivo: {str(e)}")


@router.post("/admin/catalog/upload")
async def admin_upload_catalog_file(
    bucket: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a dataset or script directly to a MinIO bucket as an administrator."""[cite: 23]
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    try:
        upload_file_to_datalake(bucket, file.file, file.filename, current_user.username)
        return JSONResponse(content={"status": "success", "message": f"Arquivo '{file.filename}' enviado para o bucket '{bucket}' com sucesso!"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao enviar arquivo: {str(e)}")


@router.delete("/admin/account/self")
async def admin_self_delete(req: SelfDeleteRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete the current administrator account after exact phrase confirmation."""[cite: 23]
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    expected_phrase = f"DELETAR CONTA {current_user.username}"
    if req.confirmation_phrase != expected_phrase:
        raise HTTPException(status_code=400, detail=f"Frase incorreta. Você deve digitar exatamente: '{expected_phrase}'")
    
    db.delete(current_user)
    db.commit()

    return JSONResponse(content={"status": "success", "message": "Sua conta de administrador foi permanentemente excluída."})


@router.post("/admin/users/{user_id}/reset-password")
async def admin_reset_user_password(user_id: int, req: UserPasswordResetRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Reset a user's password and require first-access setup and new 2FA pairing."""[cite: 23]
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    if user.role == "admin" and user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Para gerenciar sua conta admin, utilize as opções de perfil ou auto-exclusão.")

    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="A senha temporária deve ter pelo menos 8 caracteres.")

    user.hashed_password = pwd_context.hash(req.new_password)
    user.must_change_password = True
    user.is_2fa_verified = False
    user.otp_secret = None  
    db.commit()

    return JSONResponse(content={"status": "success", "message": f"Senha do usuário '{user.username}' resetada com sucesso!"})


@router.get("/admin/hardware/telemetry/advanced")
async def admin_hardware_telemetry_advanced(current_user: User = Depends(get_current_user)):
    """Varre a rede Swarm buscando os agentes de telemetria em todos os nós (Apenas Admin)"""[cite: 23]
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado.")
    
    cluster_nodes = []
    try:
        for svc in docker_client.services.list():
            if "telemetry-agent" in svc.name:
                for task in svc.tasks(filters={"desired-state": "running"}):
                    for network in task.get("NetworksAttachments", []):
                        for addr in network.get("Addresses", []):
                            ip = addr.split("/")[0]
                            try:
                                response = httpx.get(f"http://{ip}:5000/metrics", timeout=3.0)
                                if response.status_code == 200:
                                    cluster_nodes.append(response.json())
                            except Exception:
                                pass
    except Exception as e:
        print(f"Erro na telemetria avançada: {e}")

    totais = {
        "cpus_intel": sum(1 for n in cluster_nodes if n.get("marca_cpu") == "Intel"),
        "cpus_amd": sum(1 for n in cluster_nodes if n.get("marca_cpu") == "AMD"),
        "cpus_qualcomm": sum(1 for n in cluster_nodes if n.get("marca_cpu") == "Qualcomm"),
        "cpus_outros": sum(1 for n in cluster_nodes if n.get("marca_cpu") not in ["Intel", "AMD", "Qualcomm"]),
        "ram_total": sum(n.get("ram_gb", 0) for n in cluster_nodes),
        "ram_usada": sum(n.get("ram_usada_gb", 0) for n in cluster_nodes),
        "disk_total": sum(n.get("disk_gb", 0) for n in cluster_nodes),
        "disk_usado": sum(n.get("disk_usado_gb", 0) for n in cluster_nodes),
        "cores_total": sum(n.get("cores", 0) for n in cluster_nodes)
    }

    return JSONResponse(content={"status": "success", "nodes": cluster_nodes, "totais": totais})


@router.get("/admin/tailscale/status")
async def admin_tailscale_status(current_user: User = Depends(get_current_user)):
    """Busca o status da rede mesh do Tailscale em tempo real."""[cite: 23]
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    try:
        result = subprocess.run(
            ["/usr/bin/tailscale", "status", "--json"], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        if result.returncode != 0:
            raise Exception(f"Falha ao executar Tailscale: {result.stderr}")

        ts_data = json.loads(result.stdout)
        peers = []
        self_node = ts_data.get("Self", {})
        
        if self_node:
            peers.append({
                "hostname": self_node.get("HostName"),
                "ip": self_node.get("TailscaleIPs", [""])[0],
                "os": self_node.get("OS"),
                "version": self_node.get("TailscaleVersion", "").split("-")[0],
                "status": "Connected" if self_node.get("Online") else "Offline",
                "is_self": True
            })

        for pubkey, peer in ts_data.get("Peer", {}).items():
            peers.append({
                "hostname": peer.get("HostName"),
                "ip": peer.get("TailscaleIPs", [""])[0],
                "os": peer.get("OS"),
                "version": peer.get("TailscaleVersion", "").split("-")[0],
                "status": "Connected" if peer.get("Online") else "Offline",
                "is_self": False
            })

        return JSONResponse(content={"status": "success", "network": peers})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": f"Erro ao consultar Tailscale: {str(e)}"}, status_code=500)