"""
app/auth/schemas.py
────────────────────
Pydantic request/response schemas for authentication endpoints.
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ── Register ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=255, description="Your business or organization name")
    email: EmailStr = Field(..., description="Your login email address")
    password: str = Field(..., min_length=6, max_length=128, description="Password (min 6 characters)")


class RegisterResponse(BaseModel):
    client_id: str
    business_name: str
    email: str
    message: str


# ── Login ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Your registered email address")
    password: str = Field(..., min_length=1, description="Your password")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    client_id: str
    business_name: str
    expires_in: int  # seconds


# ── JWT Token Payload ─────────────────────────────────────────────────────────

class TokenData(BaseModel):
    client_id: str
    email: str
