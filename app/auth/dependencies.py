"""
app/auth/dependencies.py
─────────────────────────
FastAPI dependency that protects all /api/* routes with JWT auth.

Usage in any route:
    current_client: Client = Depends(get_current_client)

This automatically:
    1. Reads the 'Authorization: Bearer <token>' header
    2. Decodes and validates the JWT
    3. Loads the Client from the database
    4. Returns the Client ORM object to the route handler
    5. Raises HTTP 401 if anything is invalid
"""

import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Client
from app.auth.utils import decode_access_token

logger = logging.getLogger(__name__)

# ── Bearer token extractor ────────────────────────────────────────────────────
# HTTPBearer reads the Authorization header and extracts the token.
# auto_error=True → automatically returns 403 if header is missing entirely.
bearer_scheme = HTTPBearer(auto_error=True)


def get_current_client(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Client:
    """
    FastAPI dependency — validates JWT and returns the authenticated Client.

    Inject into any route to require authentication:
        @router.get("/protected")
        def my_route(client: Client = Depends(get_current_client)):
            return {"hello": client.business_name}

    Args:
        credentials: Extracted Bearer token from Authorization header.
        db:          Database session from get_db().

    Returns:
        Client ORM object for the authenticated tenant.

    Raises:
        HTTP 401: Token invalid/expired.
        HTTP 404: Client not found (e.g. deleted after token issued).
    """
    # ── Step 1: Decode JWT ────────────────────────────────────────────────────
    token_data = decode_access_token(credentials.credentials)

    # ── Step 2: Load client from DB ───────────────────────────────────────────
    client = db.query(Client).filter(Client.id == token_data.client_id).first()

    if client is None:
        logger.warning(f"JWT valid but client not found: {token_data.client_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client account not found. It may have been deleted.",
        )

    logger.debug(f"Authenticated: {client.email} ({client.id})")
    return client
