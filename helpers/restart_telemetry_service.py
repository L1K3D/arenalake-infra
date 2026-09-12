#!/usr/bin/env python3
import subprocess
import sys

def main():
    print("🔄 Buscando o serviço do Telemetry Agent no Swarm...")
    
    try:
        # Pega a lista de todos os nomes de serviços rodando no Swarm
        result = subprocess.run(
            ["docker", "service", "ls", "--format", "{{.Name}}"], 
            capture_output=True, text=True, check=True
        )
        services = result.stdout.splitlines()
        
        # Encontra dinamicamente o serviço que contém 'telemetry-agent'
        target_service = next((svc for svc in services if "telemetry-agent" in svc), None)
        
        if not target_service:
            print("❌ Serviço do Telemetry Agent não encontrado no Docker Swarm.")
            print("Certifique-se de estar rodando este script no nó MASTER.")
            sys.exit(1)
            
        print(f"🚀 Reiniciando forçadamente o serviço: {target_service}...")
        subprocess.run(["docker", "service", "update", "--force", target_service], check=True)
        
        print("\n✅ Serviço atualizado com sucesso no Swarm!")
        print("Os workers estão recriando os containers com a nova versão da imagem.")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erro de comunicação com o Docker Swarm. Código: {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    main()