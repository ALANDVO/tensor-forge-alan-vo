"""Pydantic request/response schemas for the forge API."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ForgeRequest(BaseModel):
    source: str = Field(..., min_length=1, description="Python source code to analyze.")
    language: str = Field("python", description="Source language. Currently 'python'.")
    program_name: str = Field(..., min_length=1, max_length=128,
                              description="Command name used in rendered CLI commands.")

    @field_validator("source")
    @classmethod
    def source_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source must contain code")
        return v


class ArgumentSchema(BaseModel):
    name: str
    py_type: str
    cli_type: str
    required: bool
    default: Optional[str] = None
    help: str = ""


class CommandSchema(BaseModel):
    name: str
    kind: str
    docstring: str
    location: str
    arguments: list[ArgumentSchema] = Field(default_factory=list)
    rendered: str = ""


class ForgeResponse(BaseModel):
    program_name: str
    language: str
    commands: list[CommandSchema] = Field(default_factory=list)
    error: Optional[str] = None


class SavedForgeSchema(BaseModel):
    id: int
    program_name: str
    language: str
    command_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ForgeDetailSchema(SavedForgeSchema):
    source: str
    result: dict
    source_sha: str


__all__ = [
    "ArgumentSchema", "CommandSchema", "ForgeRequest", "ForgeResponse",
    "ForgeDetailSchema", "SavedForgeSchema",
]