#!/usr/bin/env python3
import subprocess
import os
import sys

def main():
    print("🔄 Iniciando reconstrução do Telemetry Agent no Worker...")
    
    # Caminhos base baseados no seu log
    base_dir = "/opt/arenalake-prod"
    agent_dir = os.path.join(base_dir, "telemetry-agent")
    
    if not os.path.exists(agent_dir):
        print(f"❌ Diretório não encontrado: {agent_dir}")
        print("Certifique-se de estar rodando este script dentro do Worker correto.")
        sys.exit(1)

    try:
        print("\n📥 1/2 Atualizando repositório (git pull)...")
        subprocess.run(["git", "pull"], cwd=base_dir, check=True)
        
        print("\n🏗️ 2/2 Construindo a nova imagem Docker...")
        # Usando o nome EXATO da imagem que o Master está aguardando
        image_name = "arenalake-telemetry:latest"
        subprocess.run(["docker", "build", "-t", image_name, "."], cwd=agent_dir, check=True)
        
        print("\n✅ Build concluído com sucesso!")
        print("A imagem local foi atualizada. Agora rode o script de restart no Master.")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erro durante a execução do comando. Código de saída: {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    main()