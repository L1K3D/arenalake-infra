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

# Importação dos submódulos modularizados no lugar do antigo api.py monolítico
from routers import admin, bi, catalog, jobs, terminal, ui, auth

# Initialize the FastAPI application
app = FastAPI(
    title="ArenaLake Enterprise Portal",
    version="1.0.0"
)

# Mount static file directory
# Serves CSS, JavaScript, and other static assets from /static path
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register API, Authentication, UI, and Modular Routers
app.include_router(ui.router)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(bi.router)
app.include_router(jobs.router)
app.include_router(admin.router)
app.include_router(terminal.router)

# Entry point for development server
# Starts Uvicorn ASGI server on 0.0.0.0:8000
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)