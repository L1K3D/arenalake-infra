# 🚀 ArenaLake

[![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Modern-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Spark](https://img.shields.io/badge/Apache-Spark-E25A1C?logo=apachespark)](https://spark.apache.org/)
[![MinIO](https://img.shields.io/badge/MinIO-S3%20Compatible-C72E49)](https://min.io/)

**Academic Big Data & Plug-and-Play Data Lake Platform**

ArenaLake is a containerized data platform designed to simplify the setup and operation of a modern data lake environment for academic, experimentation, and learning use cases. The project combines distributed storage, orchestration, analytics processing, and isolated developer workspaces into a single integrated environment optimized for practical data engineering and data science workflows.

The project was conceived within the context of Computer Engineering at Faculdade Engenheiro Salvador Arena (FESA), with the goal of making complex infrastructure approachable for students, researchers, and engineers. Instead of requiring deep operational knowledge of Docker, Spark, MinIO, and orchestration tooling, ArenaLake abstracts those components behind a unified control plane and a user-friendly portal.

---

## Table of Contents

- [Overview](#overview)
- [Core Objectives](#core-objectives)
- [Main Features](#main-features)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Operational Model](#platform-behavior-and-operational-model)
- [Project Structure](#project-structure)
- [Data Catalog and User Experience](#data-catalog-and-user-experience)
- [Security Model](#security-model)
- [Local Deployment](#local-deployment)
- [Practical Usage Examples](#practical-usage-examples)
- [FAQ](#faq)
- [Troubleshooting](#troubleshooting)
- [Future Expansion Possibilities](#future-expansion-possibilities)
- [Summary](#summary)
- [License](#license)

---

## Overview

ArenaLake aims to provide a complete and reproducible environment for:

- provisioning isolated workspace environments for users
- managing access to a shared data lake
- running distributed data processing jobs with Apache Spark
- monitoring infrastructure resources and active services in real time
- exposing a simple and visual administration panel for platform operations

At a high level, the platform is structured around an orchestration layer, a web control panel, a data storage layer, and a compute layer. These components work together to deliver an experience similar to a managed research or analytics environment without requiring the user to manually configure the underlying stack.

---

## Core Objectives

ArenaLake was designed to answer a few practical needs:

1. **Reduce operational friction**
   - simplify the setup of analytics infrastructure for educational and prototyping scenarios

2. **Provide isolated workspaces**
   - allow users to run code in environment-specific containers without cross-user interference

3. **Expose data lake operations visually**
   - enable users to upload, inspect, and preview data inside object storage through a browser

4. **Support distributed processing**
   - integrate Spark jobs and monitoring for data transformation workloads and analytics execution

5. **Offer a clear operational dashboard**
   - allow administrators to manage users, active workspaces, cluster status, and critical actions through a central interface

---

## Main Features

### 1. Dynamic workspace provisioning
The system allows users to provision isolated environments based on access profiles. Each workspace can be treated as a dedicated experimental sandbox with the tools needed for data processing and scripting.

### 2. Browser-based portal
The platform includes a FastAPI-driven portal with user authentication, admin controls, workspace management, dashboards, and operational views. This is the main entry point used to interact with the platform.

### 3. MinIO-backed data lake
ArenaLake integrates object storage through MinIO, which acts as a S3-compatible data layer. This enables bucket-based organization, file upload operations, dataset preview, and the management of data artifacts used in analytics flows.

### 4. Spark integration
The environment includes a Spark master service for data processing tasks. This makes the platform suitable for distributed processing scenarios, experimentation with ETL pipelines, and running analytical workloads over local or bucket-based data sources.

### 5. Real-time infrastructure monitoring
The platform monitors the Docker daemon and associated resources so users can view CPU, memory, and workload status in near real time. This helps users understand the impact of job execution and the health of running services.

### 6. Admin and governance controls
The platform supports administrative actions such as:

- registering and managing users
- resetting passwords
- checking 2FA status
- inspecting active workspaces
- terminating sessions
- auditing file volumes
- managing the data catalog
- handling self-removal or destructive action control

---

## Technology Stack

The platform combines a set of complementary technologies:

- **FastAPI**: backend API and web application layer
- **Python**: service logic, orchestration, auth, and automation
- **SQLAlchemy**: database access and model layer
- **Docker & Docker Compose**: container lifecycle and service orchestration
- **Traefik**: edge routing and reverse proxying
- **Apache Spark**: distributed analytics engine
- **MinIO**: S3-compatible object storage
- **Boto3 / S3 libraries**: object storage interaction
- **PyArrow / Pandas**: data processing and preview capabilities
- **Jinja2**: HTML template rendering for the portal
- **HTML / CSS / JavaScript**: user interface and dashboard experience
- **PyOTP + QRCode**: two-factor authentication workflow
- **Passlib + Python-Jose**: password security and token-based auth

This stack was selected to balance accessibility, flexibility, and operational realism for a training-oriented data platform.

---

## Architecture

ArenaLake follows a layered architecture with clear separation of concerns.

### 1. Entry layer
The external entry point is Traefik, which routes incoming requests to the correct internal service. It acts as a gateway for the main user-facing portal and exposes the platform endpoints through a clean network layer.

### 2. Application layer
The portal application, located under `portal-compute`, is the main operational control center. It exposes REST endpoints and user interfaces for:

- authentication and onboarding
- dashboard rendering
- data catalog operations
- workspace lifecycle and metrics
- admin management and infrastructure actions

### 3. Storage layer
MinIO acts as the central object storage system. It stores dataset files, workspace artifacts, and bucket-based content used across the platform. This gives ArenaLake a realistic data-lake workflow with S3-like semantics.

### 4. Compute layer
The Spark master service is used to execute horizontal processing workloads. The environment is designed to support data transformations, experimentation, and analytics tasks aligned with Big Data learning scenarios.

### 5. Container orchestration layer
Docker and Docker Compose orchestrate the platform services and allow the backend to inspect host resources and manage sibling containers. This is a key design point because it enables the application to create or monitor isolated work environments without requiring manual system administration from end users.

---

## Platform Behavior and Operational Model

The project is designed around a real operational workflow:

1. A user accesses the portal.
2. They authenticate and optionally complete the onboarding and 2FA setup.
3. They select a workspace profile or environment configuration.
4. The backend provisions an isolated containerized workspace.
5. The user interacts with a data catalog and can upload or inspect datasets from MinIO.
6. The user can execute processing tasks or analytical scripts through the platform.
7. System metrics and Spark job states are displayed in the dashboard.
8. Administrators monitor activity and manage access and infrastructure-critical decisions.

This flow creates a practical environment where users are not just studying data tools, but also operating them in a realistic, container-based setting.

---

## Project Structure

```bash
arenalake-infra/
├── .env                          # Environment variables and credentials
├── .github/                     # CI/CD workflows and automation
│   └── workflows/
│       └── publish-workspace.yml
├── docker-compose.yml           # Unified infrastructure composition
├── deploy/                      # Traefik and deployment-related configuration
│   └── traefik/
│       └── traefik.yml
├── docker/                      # Base Dockerfiles for workspace and runtime images
│   ├── Dockerfile.worker
│   └── Dockerfile.workspace
├── portal-compute/              # Main application (FastAPI + UI)
│   ├── core/                    # Backend core modules and integrations
│   │   ├── database.py
│   │   ├── docker_mgr.py
│   │   ├── init_db.py
│   │   ├── models.py
│   │   ├── s3_mgr.py
│   │   └── security.py
│   ├── routers/                 # API and presentation endpoints
│   │   ├── api.py
│   │   ├── auth.py
│   │   └── ui.py
│   ├── static/                  # CSS and JavaScript assets
│   │   ├── css/
│   │   └── js/
│   ├── templates/               # Jinja2 HTML pages
│   │   ├── admin.html
│   │   ├── dashboard.html
│   │   ├── first-access.html
│   │   ├── login.html
│   │   ├── setup.html
│   │   └── verify-otp.html
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── configs_scripts/             # Additional setup or automation scripts
│   └── install_new.py
├── add_worker.py                # Worker-related automation helper
├── backup.py                    # Backup utility for platform state
├── doctor.py                    # Infrastructure and environment diagnostics
├── install.py                   # Installation bootstrap flow
├── README.md                    # Project documentation
├── uninstall.py                 # Uninstall and cleanup utility
└── projects_data/               # Persistent volume for user projects and storage
```

---

## Data Catalog and User Experience

The graphical Data Catalog is one of the most distinctive parts of the project. It connects the portal to the MinIO storage layer and lets users:

- browse buckets and files
- preview text and structured datasets
- visualize metadata
- upload files into storage
- download or remove dataset artifacts

This enables an experience close to a traditional data platform UI, but inside a lightweight and academic project context.

---

## Security Model

The platform includes essential security mechanisms for a managed internal environment:

- authentication layer for portal access
- password handling through secure hashing utilities
- JWT-based session management
- two-factor authentication flow for account verification
- role separation between standard users and admins
- controlled administrative actions for cluster or system operations

These features help enforce separation between regular users and operational administrators while making the project realistic in terms of access controls.

---

## Local Deployment

### Prerequisites

Before running the platform, ensure the following tools are available:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- Linux or Windows with WSL2 support

### Environment configuration
Create a `.env` file at the root of the project with the required credentials and configuration values.

Example:

```bash
MINIO_ACCESS_KEY=your_username
MINIO_SECRET_KEY=your_secure_password
WORKSPACE_NETWORK=arena-network
DATALAKE_STORAGE_PATH=/path/to/shared/storage
```

The exact values may vary depending on the deployment environment, but the key idea is that the services must share a working data lake location and network context.

### Start the stack

```bash
docker compose up -d --build
```

This command builds the necessary images and starts the main services:

- Traefik
- Spark Master
- MinIO
- workspace builder image
- portal application

### Access points

- Portal UI: `http://localhost:8000`
- MinIO Console: `http://localhost:9001`
- Spark UI: `http://localhost:8080`
- Traefik Dashboard: `http://localhost:8088`

---

## Practical Usage Examples

### Example 1: using the portal as a regular user

1. Open the portal in the browser.
2. Sign in with a username and password.
3. Complete the first-access flow if prompted, including the 2FA setup.
4. Select the workspace profile and wait for the environment to initialize.
5. Navigate to the dashboard to check CPU, memory, and service health.
6. Upload a CSV or Parquet file into the Data Catalog.
7. Preview the file or inspect generated metadata.
8. Open the workspace to write or test Python/Spark code.

This flow is designed to simulate a lightweight analytics environment in which a user works with data and infrastructure through a single interface.

### Example 2: using Spark through the platform

The platform includes a Spark master service that can be used to process data with distributed jobs. A practical usage example would be:

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("ArenaLakeExample").getOrCreate()

data = [
    ("Alice", 30),
    ("Bob", 25),
    ("Carla", 40)
]

columns = ["name", "age"]

df = spark.createDataFrame(data, columns)
df.show()

df.groupBy("age").count().show()
```

This kind of job can be executed in a project workspace or submitted through the platform's processing flow to test distributed execution patterns in a realistic analytics environment.

### Example 3: generating a data catalog workflow

1. Upload a dataset into a MinIO bucket via the portal.
2. Confirm that the file appears under the Data Catalog.
3. Select a dataset from the UI.
4. Inspect the available schema or preview the beginning of the file.
5. Use the preview and metadata to decide which transformations to apply.

This is useful for educational scenarios where users need to understand how raw data is ingested, stored, and prepared for analytics.

---

## FAQ

### What is the main purpose of ArenaLake?
ArenaLake is intended to make big data and data lake infrastructure easy to explore in a self-contained, container-based environment. It is especially useful for academic, experimentation, and internal training scenarios.

### Can I use it for real production workloads?
It is designed primarily for learning, prototyping, and controlled internal use. While many components are production-like, the project should be reviewed before external production exposure.

### Do I need to manually manage Spark or MinIO?
No. The platform is designed to run those services through Docker Compose and expose their functionality through the portal and internal automation.

### Is the portal secure by default?
It includes authentication, JWT usage, password handling, and optional 2FA flow, but it should still be hardened before being used as a production-facing platform.

### Can I run this on Windows?
Yes, but Docker Desktop with WSL2 is recommended, because the project relies on Docker networking and mounted volumes that behave more reliably on a Linux-backed environment.

### Why use Docker-out-of-Docker?
It allows the backend to access the Docker daemon from within a container, which is important for monitoring and managing isolated workspaces and compute resources dynamically.

---

## Troubleshooting

### 1. Docker services do not start
Check whether Docker is running and whether the required Docker Compose version is available.

```bash
docker --version
docker compose version
```

If Docker is not running, start the Docker service or Docker Desktop and retry the stack startup.

### 2. The portal does not load
Check whether the portal container is healthy and whether the port mapping is correct.

```bash
docker compose ps
docker compose logs portal
```

If the container exited, inspect the logs to look for missing environment variables, bad imports, or startup failures.

### 3. MinIO access is failing
Validate that the `.env` file contains valid values for the MinIO credentials and that the data directory path is correct.

```bash
cat .env
```

Also confirm that the `DATALAKE_STORAGE_PATH` directory exists and is writable.

### 4. Spark jobs are not appearing or running
Check the Spark master service and the mounted job directory.

```bash
docker compose logs spark-master
ls -la ./jobs
```

A common issue is an incorrect volume mapping or a missing job directory.

### 5. Port conflicts
If one of the exposed ports is already occupied, change the host port mapping in `docker-compose.yml` or the environment variables controlling those services.

Examples:

- `TRAEFIK_DASH_PORT`
- `SPARK_UI_PORT`
- `SPARK_RPC_PORT`
- `MINIO_API_PORT`
- `MINIO_CONSOLE_PORT`

### 6. Authentication or first-access flow is stuck
Verify that the database was initialized properly and that the portal can reach its internal storage layer.

```bash
docker compose logs portal
```

If the backend cannot reach the expected database or auth dependencies, the login flow may fail to initialize.

---

## Operational Notes

### Docker-out-of-Docker pattern
One of the strongest conceptual elements of this project is the direct access to the Docker socket. This allows the backend to monitor host resources and manage containers dynamically, which is essential for a platform that provisions user workspaces and orchestrates compute execution.

### Data-first approach
ArenaLake is designed around the idea that data access and data governance are first-class concerns. The combination of MinIO, bucket-based storage, and admin controls makes the project suitable for experimentation with data lake patterns and processing pipelines.

### Academic usability
This project was intentionally built to be understandable, practical, and easy to adapt. It provides a realistic sense of how analytics and platform engineering work together without demanding a full production-grade multi-node cluster for basic local learning.

---

## Future Expansion Possibilities

This project can be extended in several directions, including:

- multi-worker Spark clusters
- SSO integration
- role-based access refinement
- persistent database tuning and migrations
- automation for backup and restore
- richer dashboards with charts and alerts
- support for additional file types and previews
- integration with external data sources and cloud object storage

---

## Summary

ArenaLake is a practical and educational data platform that connects multiple layers of modern infrastructure into a single, coherent environment. It brings together storage, analytics processing, authentication, UI orchestration, and container-driven workspaces in a way that is both understandable and functionally realistic.

The project is not just a demo of tools in isolation; it is an integrated environment designed to teach how modern data platforms are assembled, operated, and governed in practice.

---

## License

This project is intended for academic, experimental, and learning-oriented use. If you are using or extending it in a production context, it is recommended that you review security, networking, and deployment assumptions before exposing it externally.
