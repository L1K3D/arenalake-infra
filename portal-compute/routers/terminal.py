import asyncio
import paramiko
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from core.security import SECRET_KEY, ALGORITHM
from jose import jwt

router = APIRouter()

@router.websocket("/admin/terminal/{ip}")
async def web_terminal(websocket: WebSocket, ip: str, token: str = Query(...)):
    """Abre um túnel SSH via WebSocket utilizando paramiko e as chaves do host."""[cite: 23]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "admin":
            await websocket.close(code=1008)
            return
    except Exception:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname=ip, username="root", timeout=5.0)
        channel = ssh.invoke_shell()
        channel.setblocking(False)

        async def ws_to_ssh():
            try:
                while True:
                    data = await websocket.receive_text()
                    channel.send(data)
            except WebSocketDisconnect:
                pass

        async def ssh_to_ws():
            try:
                while not channel.exit_status_ready():
                    if channel.recv_ready():
                        data = channel.recv(1024).decode('utf-8', 'replace')
                        await websocket.send_text(data)
                    else:
                        await asyncio.sleep(0.01)
            except Exception:
                pass

        await asyncio.gather(ws_to_ssh(), ssh_to_ws())

    except Exception as e:
        await websocket.send_text(f"\r\n[!] Erro de conexão SSH com {ip}: {str(e)}\r\n")
    finally:
        ssh.close()
        try:
            await websocket.close()
        except:
            pass