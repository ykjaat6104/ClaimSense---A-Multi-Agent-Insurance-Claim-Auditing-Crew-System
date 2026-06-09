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


class SignupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6)
    display_name: str = Field(..., min_length=1, max_length=128)


class SignupResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    display_name: str


class ProfileResponse(BaseModel):
    username: str
    display_name: str | None
    avatar_url: str | None
    created_at: str


class UpdateProfileRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=128)


class AdjusterActionRequest(BaseModel):
    """Human decision on top of AI recommendation (audit trail)."""

    action: Literal["approve", "reject", "manual_review"]
