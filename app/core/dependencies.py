"""FastAPI dependencies"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import logger
from app.models.database import get_db
from app.schemas.token import AccessTokenPayload
from app.services.auth_service import auth_service
from app.services.oauth_client_service import oauth_client_service
from app.services.token_service import token_service
from app.services.user_service import user_service

# Database session dependency
DBSession = Annotated[AsyncSession, Depends(get_db)]


# Service dependencies
def get_user_service():
    """Get user service instance"""
    return user_service


def get_oauth_client_service():
    """Get OAuth client service instance"""
    return oauth_client_service


def get_auth_service():
    """Get auth service instance"""
    return auth_service


def get_token_service():
    """Get token service instance"""
    return token_service


# Type annotations for services
UserServiceDep = Annotated[type[user_service], Depends(get_user_service)]
OAuthClientServiceDep = Annotated[type[oauth_client_service], Depends(get_oauth_client_service)]
AuthServiceDep = Annotated[type[auth_service], Depends(get_auth_service)]
TokenServiceDep = Annotated[type[token_service], Depends(get_token_service)]


# Security and authentication dependencies
security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials, Depends(security)
    ],
) -> AccessTokenPayload:
    """
    Get current user from Authorization header
    
    Validates the access token and returns the token payload.
    Adds user information to request.state for use in request context.
    
    Args:
        request: FastAPI request object
        credentials: HTTP Bearer credentials from Authorization header
        
    Returns:
        AccessTokenPayload with user information
        
    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    token = credentials.credentials

    try:
        payload = token_service.validate_access_token(token)

        # Store user information in request state for access in handlers
        request.state.user_id = payload.sub
        request.state.client_id = payload.client_id
        request.state.scope = payload.scope

        logger.debug(
            "[TRACE] Access token validated in dependency",
            extra={
                "trace_point": "get_current_user_success",
                "user_id": payload.sub,
                "client_id": payload.client_id,
            }
        )

        return payload

    except Exception as e:
        logger.warning(
            f"[TRACE] Failed to validate access token in dependency: {e}",
            extra={"trace_point": "get_current_user_failed"}
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
        ) from e


# Type alias for authenticated endpoints
CurrentUser = Annotated[AccessTokenPayload, Depends(get_current_user)]
