"""Authentication utilities for API routes."""

import base64
import hashlib
import hmac
import json
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from air1.config import settings

security = HTTPBearer()


class AuthUser:
    """Authenticated user from JWT token."""

    def __init__(self, user_id: int, email: str):
        self.user_id = user_id
        self.email = email


def _decode_jwt(token: str) -> Optional[dict]:
    """Decode and verify a JWT token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts

        # Verify signature
        expected_signature = hmac.new(
            settings.jwt_secret.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256,
        ).digest()
        expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).rstrip(b"=").decode()

        if not hmac.compare_digest(signature_b64, expected_signature_b64):
            return None

        # Decode payload (add padding if needed)
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding

        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload
    except Exception:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthUser:
    """Dependency to get the current authenticated user from JWT token."""
    token = credentials.credentials
    payload = _decode_jwt(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Authentication required"},
        )

    # Check expiration
    import time
    if payload.get("exp", 0) < time.time():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Authentication required"},
        )

    user_id = int(payload.get("sub", 0))
    email = payload.get("email", "")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Authentication required"},
        )

    return AuthUser(user_id=user_id, email=email)
