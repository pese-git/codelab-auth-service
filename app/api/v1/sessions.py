"""Session management endpoints"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.config import logger
from app.core.dependencies import AuthServiceDep, DBSession
from app.services.session_service import session_service

router = APIRouter(prefix="/oauth/sessions", tags=["sessions"])


@router.get("")
async def list_sessions(
    request: Request,
    db: DBSession,
    auth_svc: AuthServiceDep,
):
    """
    List all active sessions for the current user
    
    Requires valid Bearer token in Authorization header.
    
    Returns:
        List of active sessions with metadata
    """
    # Get bearer token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        logger.warning(
            f"[TRACE] List sessions called without valid Bearer token",
            extra={"trace_point": "list_sessions_no_bearer"}
        )
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authorization header",
        )
    
    access_token = auth_header[7:]
    
    # Validate access token
    payload = auth_svc.validate_token(access_token)
    if not payload:
        logger.warning(
            f"[TRACE] List sessions called with invalid token",
            extra={"trace_point": "list_sessions_invalid_token"}
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid access token",
        )
    
    user_id = payload.sub
    
    logger.info(
        f"[TRACE] List sessions requested",
        extra={"trace_point": "list_sessions_start", "user_id": user_id}
    )
    
    try:
        sessions = await session_service.list_user_sessions(db, user_id)
        
        logger.debug(
            f"[TRACE] Sessions retrieved successfully",
            extra={
                "trace_point": "list_sessions_success",
                "user_id": user_id,
                "count": len(sessions),
            }
        )
        
        return JSONResponse(
            content={
                "sessions": [
                    {
                        "session_id": s["session_id"],
                        "client_id": s["client_id"],
                        "created_at": s["created_at"].isoformat(),
                        "last_used": s["last_used"].isoformat() if s["last_used"] else None,
                        "ip_address": s["ip_address"],
                        "user_agent": s["user_agent"],
                        "expires_at": s["expires_at"].isoformat(),
                    }
                    for s in sessions
                ]
            },
            status_code=200,
        )
    
    except Exception as e:
        logger.error(
            f"[TRACE] List sessions error: {e}",
            exc_info=True,
            extra={"trace_point": "list_sessions_error", "user_id": user_id}
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve sessions",
        )


@router.get("/{session_id}")
async def get_session(
    request: Request,
    db: DBSession,
    auth_svc: AuthServiceDep,
    session_id: str,
):
    """
    Get detailed information about a specific session
    
    Requires valid Bearer token and ownership of the session.
    
    Args:
        session_id: Session ID to retrieve
        
    Returns:
        Session details
    """
    # Get bearer token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authorization header",
        )
    
    access_token = auth_header[7:]
    
    # Validate access token
    payload = auth_svc.validate_token(access_token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid access token",
        )
    
    user_id = payload.sub
    
    logger.info(
        f"[TRACE] Get session requested",
        extra={
            "trace_point": "get_session_start",
            "user_id": user_id,
            "session_id": session_id,
        }
    )
    
    try:
        session_info = await session_service.get_session_info(db, user_id, session_id)
        
        if not session_info:
            logger.warning(
                f"[TRACE] Session not found or not owned by user",
                extra={
                    "trace_point": "get_session_not_found",
                    "user_id": user_id,
                    "session_id": session_id,
                }
            )
            raise HTTPException(
                status_code=404,
                detail="Session not found",
            )
        
        logger.debug(
            f"[TRACE] Session retrieved successfully",
            extra={
                "trace_point": "get_session_success",
                "user_id": user_id,
                "session_id": session_id,
            }
        )
        
        return JSONResponse(
            content={
                "session_id": session_info["session_id"],
                "client_id": session_info["client_id"],
                "scope": session_info["scope"],
                "created_at": session_info["created_at"].isoformat(),
                "last_used": session_info["last_used"].isoformat() if session_info["last_used"] else None,
                "last_rotated_at": session_info["last_rotated_at"].isoformat() if session_info["last_rotated_at"] else None,
                "ip_address": session_info["ip_address"],
                "user_agent": session_info["user_agent"],
                "expires_at": session_info["expires_at"].isoformat(),
            },
            status_code=200,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[TRACE] Get session error: {e}",
            exc_info=True,
            extra={
                "trace_point": "get_session_error",
                "user_id": user_id,
                "session_id": session_id,
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve session",
        )


@router.delete("/{session_id}")
async def revoke_session(
    request: Request,
    db: DBSession,
    auth_svc: AuthServiceDep,
    session_id: str,
):
    """
    Revoke a specific session
    
    Requires valid Bearer token and ownership of the session.
    
    Args:
        session_id: Session ID to revoke
        
    Returns:
        Revocation confirmation
    """
    # Get bearer token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authorization header",
        )
    
    access_token = auth_header[7:]
    
    # Validate access token
    payload = auth_svc.validate_token(access_token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid access token",
        )
    
    user_id = payload.sub
    
    logger.info(
        f"[TRACE] Revoke session requested",
        extra={
            "trace_point": "revoke_session_start",
            "user_id": user_id,
            "session_id": session_id,
        }
    )
    
    try:
        success = await session_service.revoke_session(db, user_id, session_id)
        
        if not success:
            logger.warning(
                f"[TRACE] Session not found for revocation",
                extra={
                    "trace_point": "revoke_session_not_found",
                    "user_id": user_id,
                    "session_id": session_id,
                }
            )
            raise HTTPException(
                status_code=404,
                detail="Session not found",
            )
        
        logger.info(
            f"[TRACE] Session revoked successfully",
            extra={
                "trace_point": "revoke_session_success",
                "user_id": user_id,
                "session_id": session_id,
            }
        )
        
        return JSONResponse(
            content={"message": f"Session {session_id} revoked successfully"},
            status_code=200,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[TRACE] Revoke session error: {e}",
            exc_info=True,
            extra={
                "trace_point": "revoke_session_error",
                "user_id": user_id,
                "session_id": session_id,
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to revoke session",
        )
