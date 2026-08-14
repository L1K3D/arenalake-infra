# ============================================================================
# ArenaLake Portal Compute - Main Application
# ============================================================================
# This module initializes the FastAPI application and configures routing.
# The server acts as the central backend for:
# - User authentication and workspace provisioning
# - Dashboard UI rendering (HTML templates)
# - REST APIs for data catalog, metrics, Spark monitoring
# - Static asset serving (CSS, JavaScript)
# ============================================================================

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import api, ui

# Initialize the FastAPI application
app = FastAPI()

# Mount static file directory
# Serves CSS, JavaScript, and other static assets from /static path
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register API and UI routers
# - ui.router: handles HTML template rendering (login, setup, dashboard pages)
# - api.router: handles REST API endpoints (/api/catalog, /api/metrics, etc.)
app.include_router(ui.router)
app.include_router(api.router)

# Entry point for development server
# Starts Uvicorn ASGI server on 0.0.0.0:8000
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)