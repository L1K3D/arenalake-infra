from fastapi import FastAPI
from routers import api, ui

app = FastAPI()

# Incluindo as rotas separadas
app.include_router(ui.router)
app.include_router(api.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
