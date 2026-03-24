"""User registration endpoint"""

import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.config import logger, settings
from app.schemas.user import UserRegister, UserRegistrationResponse
from app.services.user_service import user_service
from app.services.audit_service import audit_service
from app.services.email_service import email_service
from app.services.email_notifications import EmailNotificationService

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
        
        # Schedule background tasks for email sending (graceful degradation)
        try:
            notification_service = EmailNotificationService()
            
            # Send welcome email as background task
            if settings.send_welcome_email:
                try:
                    asyncio.create_task(
                        notification_service.send_welcome_email(user, background=False)
                    )
                    logger.debug(
                        f"Welcome email task scheduled for user {user.id}",
                        extra={"user_id": user.id},
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to schedule welcome email task: {e}",
                        extra={"user_id": user.id},
                    )
            
            # Send confirmation email as background task if required
            if settings.require_email_confirmation:
                try:
                    # Generate confirmation token
                    token = await email_service.generate_confirmation_token(user.id)
                    
                    # Save token to database
                    token_saved = await email_service.save_confirmation_token(
                        user_id=user.id,
                        token=token,
                        db=db,
                        expires_in_hours=24,
                    )
                    
                    if token_saved:
                        # Schedule confirmation email
                        asyncio.create_task(
                            email_service.send_confirmation_email(user, token, db)
                        )
                        logger.debug(
                            f"Confirmation email task scheduled for user {user.id}",
                            extra={"user_id": user.id},
                        )
                    else:
                        logger.warning(
                            f"Failed to save confirmation token for user {user.id}",
                            extra={"user_id": user.id},
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to schedule confirmation email task: {e}",
                        extra={"user_id": user.id},
                    )
        except Exception as e:
            # Log but don't fail registration - graceful degradation
            logger.error(
                f"Error scheduling email tasks: {e}",
                extra={"user_id": user.id},
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


@router.get("/confirm-email")
async def confirm_email(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm user email address using a confirmation token.
    
    Args:
        token: Email confirmation token (query parameter)
        
    Returns:
        - 200 OK: Email confirmed successfully
        - 400 Bad Request: Invalid or expired token
    """
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Verify confirmation token and get user
        user = await email_service.verify_confirmation_token(db, token)
        
        if not user:
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
            
            logger.warning(
                f"Email confirmation failed: invalid or expired token",
                extra={
                    "event_type": "EMAIL_CONFIRMATION_FAILED",
                    "client_ip": client_ip,
                },
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired confirmation token",
            )
        
        # Update user email_confirmed flag
        user.email_confirmed = True
        await db.commit()
        
        # Log successful email confirmation
        await audit_service.log(
            db=db,
            event_type="EMAIL_CONFIRMED",
            user_id=user.id,
            details={
                "email": user.email,
                "client_ip": client_ip,
                "user_agent": request.headers.get("user-agent", "unknown"),
            },
        )
        
        logger.info(
            f"Email confirmed for user {user.id}",
            extra={
                "event_type": "EMAIL_CONFIRMED",
                "user_id": user.id,
                "email": user.email,
            }
        )
        
        return {"message": "Email confirmed successfully", "user_id": user.id}
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            f"Email confirmation error: {e}",
            extra={"client_ip": client_ip},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during email confirmation",
        )
