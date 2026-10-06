from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routes.verification import router

app = FastAPI(title="LabelCheck")

# backend/app/main.py -> project root is two folders up.
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

# The website runs on port 5173 and this server runs on port 8000.
# The browser blocks that cross-port request unless the server allows it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    """Serve the website when it has been built. Otherwise confirm the server is up."""
    index = FRONTEND_DIST / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {
        "app": "LabelCheck",
        "status": "ok",
        "message": "Backend is running",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST), name="frontend")
