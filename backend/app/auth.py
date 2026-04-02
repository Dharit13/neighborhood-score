import json
import logging
import os

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

_security = HTTPBearer(auto_error=False)

# Supabase JWT signing — supports both HS256 (legacy secret) and ES256 (JWK)
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_JWT_JWK = os.getenv("SUPABASE_JWT_JWK", "")

_signing_key = None


def _get_signing_key():
    global _signing_key
    if _signing_key is not None:
        return _signing_key, ["ES256"] if SUPABASE_JWT_JWK else ["HS256"]

    if SUPABASE_JWT_JWK:
        jwk_data = json.loads(SUPABASE_JWT_JWK)
        _signing_key = jwt.PyJWK(jwk_data).key
        return _signing_key, ["ES256"]
    elif SUPABASE_JWT_SECRET:
        _signing_key = SUPABASE_JWT_SECRET
        return _signing_key, ["HS256"]
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Auth not configured on server")


def _decode_token(token: str) -> dict:
    key, algorithms = _get_signing_key()
    try:
        return jwt.decode(token, key, algorithms=algorithms, audience="authenticated")
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
