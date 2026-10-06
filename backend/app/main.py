from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.verification import router

app = FastAPI(title="LabelCheck")

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
    """Confirms the server is up. The real label check comes in a later phase."""
    return {
        "app": "LabelCheck",
        "status": "ok",
        "message": "Backend is running",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
