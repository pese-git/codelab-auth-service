"""Password reset schemas"""

from pydantic import BaseModel, EmailStr, Field


class PasswordResetRequest(BaseModel):
    """Schema for password reset request"""

    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation"""

    token: str = Field(..., min_length=20, description="Password reset token")
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="New password (8-72 characters)",
    )
    password_confirm: str = Field(
        ...,
        description="Password confirmation (must match password)",
    )

    def validate(self) -> tuple[bool, str | None]:
        """Validate password reset confirm data"""
        if self.password != self.password_confirm:
            return False, "Passwords do not match"
        return True, None


class PasswordResetResponse(BaseModel):
    """Schema for password reset response"""

    message: str = Field(..., description="Response message")
