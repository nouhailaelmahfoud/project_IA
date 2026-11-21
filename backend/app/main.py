from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import jobs
from backend.app.core.config import SUPPORTED_LANGUAGES

app = FastAPI(title="Migration Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # React (Create React App)
        "http://localhost:5173",   # React (Vite)
        "http://localhost:8501",   # Streamlit
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/languages")
def languages():
    return {"languages": list(SUPPORTED_LANGUAGES)}