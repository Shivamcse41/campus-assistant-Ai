"""
app/auth/router.py
───────────────────
Authentication endpoints for CampConnect SaaS.

Endpoints:
    POST /auth/register  — Create a new client account (bcrypt password)
    POST /auth/login     — Authenticate and receive a JWT token
    GET  /auth/me        — Get current client profile (requires JWT)
"""

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Client
from app.auth.schemas import (
    RegisterRequest, RegisterResponse,
    LoginRequest, LoginResponse,
)
from app.auth.utils import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── POST /auth/register ───────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new client (business) account",
)
def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    """
    Create a new tenant account on CampConnect.

    - Checks for duplicate email
    - Hashes password with bcrypt (never stored plain)
    - Creates a Client record with a UUID primary key
    - Returns the client_id to use in /api/* endpoints

    After registering, call **POST /auth/login** to get your JWT token.
    """
    # ── Check for duplicate email ─────────────────────────────────────────────
    existing = db.query(Client).filter(Client.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account with email '{body.email}' already exists. "
                   f"Please login instead.",
        )

    # ── Hash password ─────────────────────────────────────────────────────────
    hashed = hash_password(body.password)

    # ── Create client record ──────────────────────────────────────────────────
    client = Client(
        business_name=body.business_name,
        email=body.email,
        hashed_password=hashed,
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    logger.info(f"New client registered: {client.id} | {body.email} | {body.business_name}")

    return RegisterResponse(
        client_id=client.id,
        business_name=client.business_name,
        email=client.email,
        message=(
            f"Account created successfully for '{body.business_name}'. "
            f"Use POST /auth/login to get your access token."
        ),
    )


# ── POST /auth/login ──────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login and receive a JWT access token",
)
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """
    Authenticate with email and password.

    Returns a **JWT Bearer token** valid for 24 hours.

    Include this token in all `/api/*` requests as:
    ```
    Authorization: Bearer <your_token_here>
    ```
    """
    # ── Look up client by email ───────────────────────────────────────────────
    client = db.query(Client).filter(Client.email == body.email).first()

    # ── Verify password ───────────────────────────────────────────────────────
    # Use a single generic error message for both "not found" and "wrong password"
    # to prevent user enumeration attacks.
    if not client or not verify_password(body.password, client.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ── Create JWT token ──────────────────────────────────────────────────────
    token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": client.id,       # Subject: client UUID
            "email": client.email,  # Extra claim for easy identification
        },
        expires_delta=token_expires,
    )

    logger.info(f"Login successful: {client.email} ({client.id})")

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        client_id=client.id,
        business_name=client.business_name,
        expires_in=int(token_expires.total_seconds()),
    )


# ── GET /auth/me ──────────────────────────────────────────────────────────────

@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated client profile",
)
def get_me(
    current_client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """
    Returns the profile of the currently authenticated client.
    Requires a valid JWT Bearer token.
    """
    from sqlalchemy import func
    from app.models import Document, QueryLog

    doc_count = db.query(func.count(Document.id)).filter(
        Document.client_id == current_client.id
    ).scalar() or 0

    query_count = db.query(func.count(QueryLog.id)).filter(
        QueryLog.client_id == current_client.id
    ).scalar() or 0

    return {
        "client_id": current_client.id,
        "business_name": current_client.business_name,
        "email": current_client.email,
        "created_at": current_client.created_at.isoformat(),
        "documents_uploaded": doc_count,
        "total_queries": query_count,
    }
