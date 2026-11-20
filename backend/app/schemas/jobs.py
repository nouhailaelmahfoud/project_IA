from typing import Any, Optional
from pydantic import BaseModel


class JobCreated(BaseModel):
    job_id: str
    language: str
    status: str


class JobStatus(BaseModel):
    job_id: str
    language: str
    status: str                       # pending | running | done | failed
    issues: list[dict[str, Any]] = []
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None

class MigrateRequest(BaseModel):
    mode: str = "rules_only"          # rules_only | hybrid | llm_only
    provider: str = "openrouter"      # openrouter | ollama (ignoré en rules_only)
    model: Optional[str] = None
    max_iterations: int = 3