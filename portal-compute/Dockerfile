# ============================================================================
# ArenaLake Portal Compute API Server
# ============================================================================
# This Dockerfile containerizes the FastAPI backend for the ArenaLake platform.
# The server provides REST APIs for workspace management, data catalog, and
# Spark cluster monitoring, along with the web UI for user dashboards.
# ============================================================================

# Base image: Python 3.11 slim (lightweight, minimal dependencies)
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements file and install Python dependencies
# Installed packages include FastAPI, Uvicorn, boto3, Docker client, etc.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code into the container
COPY . .

# Entrypoint: Start Uvicorn ASGI server
# - main:app refers to the FastAPI app instance in main.py
# - --host 0.0.0.0 makes the server accessible from outside the container
# - --port 8000 exposes the API on port 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
