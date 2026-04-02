import json
import logging
import os

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

_security = HTTPBearer(auto_error=False)

SUPABASE_JWT_JWK = os.getenv("SUPABASE_JWT_JWK", "")

_public_key = None


def _get_public_key():
    global _public_key
    if _public_key is not None:
        return _public_key
    if not SUPABASE_JWT_JWK:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Auth not configured on server")
    jwk_data = json.loads(SUPABASE_JWT_JWK)
    _public_key = jwt.PyJWK(jwk_data).key
    return _public_key


def _decode_token(token: str) -> dict:
    key = _get_public_key()
    try:
        return jwt.decode(token, key, algorithms=["ES256"], audience="authenticated")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.error("JWT decode failed: %s", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return _decode_token(credentials.credentials)
