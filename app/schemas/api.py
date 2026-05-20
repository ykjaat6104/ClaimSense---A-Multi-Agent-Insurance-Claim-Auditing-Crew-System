from typing import Literal

from pydantic import BaseModel, Field


class ClaimUploadResponse(BaseModel):
    claim_id: str = Field(..., description="UUID of the created claim")
    status: str
    message: str = "Files stored. Start analysis from the dashboard."


class ProcessResponse(BaseModel):
    claim_id: str
    status: str
    message: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class AdjusterActionRequest(BaseModel):
    """Human decision on top of AI recommendation (audit trail)."""

    action: Literal["approve", "reject", "manual_review"]
