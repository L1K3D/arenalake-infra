# 🚀 ArenaLake

**Plataforma Acadêmica de Big Data & Data Lake Plug-and-Play**

O **ArenaLake** é uma infraestrutura completa de Data Lake conteinerizada, desenvolvida para facilitar o estudo, a engenharia e a análise de grandes volumes de dados (Big Data). O projeto nasceu com o intuito de entregar um ambiente acadêmico robusto para simular o mundo real de processamento de dados, integrando armazenamento distribuído, orquestração e workspaces isolados em uma única solução.

Desenvolvido no contexto de Engenharia de Computação da Faculdade Engenheiro Salvador Arena (FESA), o ArenaLake elimina a complexidade de configuração de infraestrutura, permitindo que engenheiros e cientistas de dados foquem no que importa: o código.

---

## 🎯 O que é o projeto?

O ArenaLake funciona como um portal unificado onde o usuário pode:
1. **Provisionar Ambientes Dinâmicos:** Escolher perfis de hardware (`Standard` ou `Extreme`) e iniciar um container isolado do VS Code (Code Server) já pré-configurado com PySpark.
2. **Explorar o Data Lake:** Uma interface gráfica (*Data Catalog*) conectada ao MinIO, permitindo uploads, visualização de metadados e preview de arquivos CSV, TXT, imagens e Parquet.
3. **Monitorar Processamento:** Um painel de controle que consome métricas do Docker Daemon do host e da API do Apache Spark para exibir o consumo de CPU/RAM e o avanço em tempo real de *jobs* e *tasks* distribuídas.

---

## 🛠️ Tecnologias Utilizadas

*   **FastAPI & Python:** Backend orquestrador, responsável pela API REST, rotas da UI e comunicação via SDKs.
*   **Apache Spark:** Motor de processamento distribuído (arquitetura Master/Worker).
*   **MinIO (S3 Compatible):** Object Storage atuando como o Data Lake para as camadas Bronze, Silver e Gold.
*   **Traefik:** Reverse proxy e gateway para gerenciar rotas dinâmicas e balanceamento.
*   **Docker & Docker Compose:** Containerização e orquestração local via Docker-out-of-Docker (DooD).
*   **Boto3 & PyArrow:** Interação e extração de amostras de arquivos `.parquet` e `.csv` no MinIO.
*   **HTML5, CSS3, JS & Chart.js:** Frontend modularizado sem frameworks pesados, garantindo alta velocidade e renderização nativa.

---

## 🏗️ Como foi construído (Arquitetura)

O ArenaLake foi arquitetado seguindo princípios de modularidade e separação de responsabilidades (inspirado no padrão Router-Service do FastAPI):

1. **Gestão de Infraestrutura (DooD):** O grande diferencial técnico é a utilização de *Docker-out-of-Docker*. O backend FastAPI possui o socket do Docker mapeado (`/var/run/docker.sock`), permitindo que a aplicação consulte o hardware do host (CPU/RAM reais) e gerencie o ciclo de vida de *sibling containers* (Workspaces do VS Code e Workers do Spark) dinamicamente.
2. **Integração Backend-S3:** O módulo `s3_mgr.py` atua como ponte segura entre a UI e o MinIO, gerando URLs assinadas (presigned URLs) para visualização de mídias e decodificando bytes de arquivos Parquet em *DataFrames* Pandas para preview no Data Catalog.
3. **Frontend Otimizado:** As *views* (arquivos Jinja2 em `templates/`) interagem com o backend servindo arquivos estáticos purificados (`static/css` e `static/js`), permitindo *polling* assíncrono para atualizar gráficos de CPU/RAM sem onerar o carregamento da página.

---

## 🚀 Como Rodar Localmente

### Pré-requisitos
*   [Docker](https://docs.docker.com/get-docker/) (v20.10+) e [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+) instalados.
*   Sistema operacional Linux ou Windows com WSL2.

### Passo a Passo

**1. Clone o repositório**
```bash
git clone [https://github.com/seu-usuario/arenalake-infra.git](https://github.com/seu-usuario/arenalake-infra.git)
cd arenalake-infra
```

**2. Configure o Ambiente**
Crie um arquivo ```.env``` na raiz do projeto contendo as credenciais de acesso para o Data Lake:
```bash
MINIO_ACCESS_KEY=seu_username
MINIO_SECRET_KEY=sua_senha_segura
```

**3. Inicialize a infraestrutura**
Basta utilizar o Docker Compose. Ele irá construir a imagem base do Workspace automaticamente e subir os serviços core:
```bash
docker compose up -d --build
```

**4. Acesse o seu ArenaLake**
- Portal de acesso: http://localhost:8000
- MinIO Console (Painel Nativo): http://localhost:9001
- Spark Master UI: http://localhost:8080
- Traefik Dashboard: http://localhost:8088

Para logar no portal, basta digitar qualquer nome de usuário e uma senha qualquer (a autenticação em modo sandbox provisionará um ambiente dedicado com base no nome de usuário informado).

---

## 📂 Estrutura de Diretórios

```bash
arenalake-infra/
├── .env                        # Credenciais e variáveis de ambiente
├── docker-compose.yml          # Orquestrador unificado da plataforma
├── deploy/                     # Configurações do Traefik e Proxies
├── docker/                     # Dockerfiles base (VS Code Workspace e Workers)
├── jobs/                       # Scripts Spark de exemplo
├── portal-compute/             # Aplicação Web (FastAPI)
│   ├── core/                   # Integrações pesadas (Docker SDK e Boto3)
│   ├── routers/                # Controladores (API de métricas e Renderização UI)
│   ├── static/                 # Arquivos CSS e JS modularizados
│   └── templates/              # Interfaces HTML base
└── projects_data/              # Volume persistente para os projetos dos usuários
```