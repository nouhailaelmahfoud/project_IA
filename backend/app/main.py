from fastapi import FastAPI

from backend.app.api import jobs
from backend.app.core.config import SUPPORTED_LANGUAGES

app = FastAPI(title="Migration Agent API", version="0.1.0")
app.include_router(jobs.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/languages")
def languages():
    return {"languages": list(SUPPORTED_LANGUAGES)}