"""Formats de sortie attendus des agents (validés par Pydantic)."""
from typing import Optional, Union

from pydantic import BaseModel, Field


class Risk(BaseModel):
    line: Optional[Union[int, str]] = None
    description: str
    suggestion: str = ""


class AnalysisOutput(BaseModel):
    risks: list[Risk] = Field(default_factory=list)


class MigrationOutput(BaseModel):
    code: str
    changes: list[str] = Field(default_factory=list)


class ReviewOutput(BaseModel):
    approved: bool
    problems: list[str] = Field(default_factory=list)
