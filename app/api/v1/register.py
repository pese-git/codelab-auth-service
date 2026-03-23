"""User registration endpoint"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.config import logger, settings
from app.schemas.user import UserRegister, UserRegistrationResponse
from app.services.user_service import user_service
from app.services.audit_service import audit_service
from app.services.email_service import email_service

router = APIRouter(prefix="/api/v1", tags=["Registration"])


@router.post(
    "/register",
    response_model=UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "User successfully registered"},
        409: {"description": "Email or username already registered"},
        422: {"description": "Invalid input data"},
        429: {"description": "Too many registration attempts"},
    },
)
async def register(
    request: Request,
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> UserRegistrationResponse:
    """
    Register a new user.
    
    - **email**: Valid email address (RFC 5322)
    - **username**: 3-20 characters, alphanumeric, dash, underscore
    - **password**: 8-128 characters
    
    Returns:
        - 201 Created: User successfully registered
        - 409 Conflict: Email or username already registered
        - 422 Unprocessable Entity: Invalid input data
        - 429 Too Many Requests: Rate limit exceeded
    """
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Attempt to register user
        user = await user_service.register_user(db, user_data)
        
        # Log successful registration
        await audit_service.log(
            db=db,
            event_type="REGISTRATION_ATTEMPT_SUCCESS",
            user_id=user.id,
            details={
                "email": user.email,
                "username": user.username,
                "client_ip": client_ip,
                "user_agent": request.headers.get("user-agent", "unknown"),
            },
        )
        
        logger.info(
            f"User registered successfully: {user.id}",
            extra={
                "event_type": "REGISTRATION_SUCCESS",
                "user_id": user.id,
                "username": user.username,
                "client_ip": client_ip,
            }
        )
        
        # Return response with Location header
        return UserRegistrationResponse.model_validate(user)
    
    except ValueError as e:
        error_msg = str(e)
        
        # Determine if it's email or username conflict
        is_email_conflict = "email" in error_msg.lower()
        is_username_conflict = "username" in error_msg.lower()
        
        # Log failed registration attempt
        event_type = (
            "REGISTRATION_DUPLICATE_EMAIL"
            if is_email_conflict
            else "REGISTRATION_DUPLICATE_USERNAME"
        )
        
        await audit_service.log(
            db=db,
            event_type=event_type,
            details={
                "attempted_email": user_data.email if is_email_conflict else None,
                "attempted_username": user_data.username if is_username_conflict else None,
                "client_ip": client_ip,
                "user_agent": request.headers.get("user-agent", "unknown"),
            },
        )
        
        logger.warning(
            f"Registration failed: {error_msg}",
            extra={
                "event_type": event_type,
                "client_ip": client_ip,
            }
        )
        
        # Return generic conflict response to prevent enumeration
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Email already registered"
                if is_email_conflict
                else "Username already taken"
            ),
        )
    
    except RuntimeError as e:
        # Race condition or database error
        error_msg = str(e)
        
        # Log race condition attempt
        await audit_service.log(
            db=db,
            event_type="REGISTRATION_ATTEMPT_FAILED",
            details={
                "email": user_data.email,
                "username": user_data.username,
                "failure_reason": error_msg,
                "client_ip": client_ip,
                "user_agent": request.headers.get("user-agent", "unknown"),
            },
        )
        
        logger.error(
            f"Registration error: {error_msg}",
            extra={
                "event_type": "REGISTRATION_FAILED",
                "client_ip": client_ip,
            }
        )
        
        # Determine response based on error type
        if "race condition" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered" if "email" in error_msg.lower() else "Username already taken",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred during registration",
            )


@router.post("/confirm-email")
async def confirm_email(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm user email address using a confirmation token.
    
    Args:
        token: Email confirmation token
        
    Returns:
        - 200 OK: Email confirmed successfully
        - 400 Bad Request: Invalid or expired token
    """
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Verify confirmation token
        user_id = await email_service.verify_confirmation_token(db, token)
        
        if not user_id:
            # Token is invalid or expired
            await audit_service.log(
                db=db,
                event_type="EMAIL_CONFIRMATION_FAILED",
                details={
                    "reason": "invalid_or_expired_token",
                    "client_ip": client_ip,
                    "user_agent": request.headers.get("user-agent", "unknown"),
                },
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired confirmation token",
            )
        
        # Update user email_confirmed flag
        user = await user_service.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        user.email_confirmed = True
        await db.commit()
        
        # Log successful email confirmation
        await audit_service.log(
            db=db,
            event_type="EMAIL_CONFIRMED",
            user_id=user_id,
            details={
                "email": user.email,
                "client_ip": client_ip,
                "user_agent": request.headers.get("user-agent", "unknown"),
            },
        )
        
        logger.info(
            f"Email confirmed for user {user_id}",
            extra={
                "event_type": "EMAIL_CONFIRMED",
                "user_id": user_id,
                "email": user.email,
            }
        )
        
        return {"message": "Email confirmed successfully"}
    
    except Exception as e:
        logger.error(
            f"Email confirmation error: {e}",
            extra={"client_ip": client_ip},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during email confirmation",
        )
