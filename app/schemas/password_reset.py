"""Password reset schemas"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from app.core.config import settings
from app.utils.validators import validate_password as validate_password_rules


class PasswordResetRequest(BaseModel):
    """Schema for password reset request"""

    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation"""

    token: str = Field(..., min_length=20, description="Password reset token")
    password: str = Field(
        ...,
        min_length=settings.password_min_length,
        max_length=settings.password_max_length,
        description=f"New password ({settings.password_min_length}-{settings.password_max_length} characters)",
    )
    password_confirm: str = Field(
        ...,
        description="Password confirmation (must match password)",
    )

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, v: str) -> str:
        """Validate password requirements using centralized validation rules"""
        is_valid, error_message = validate_password_rules(v)
        if not is_valid:
            raise ValueError(error_message)
        return v

    def validate(self) -> tuple[bool, str | None]:
        """Validate password reset confirm data"""
        if self.password != self.password_confirm:
            return False, "Passwords do not match"
        return True, None


class PasswordResetResponse(BaseModel):
    """Schema for password reset response"""

    message: str = Field(..., description="Response message")
