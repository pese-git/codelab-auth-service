"""User schemas"""

import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Base user schema"""

    username: str = Field(..., min_length=3, max_length=255)
    email: EmailStr


class UserCreate(UserBase):
    """Schema for creating a user"""

    password: str = Field(..., min_length=8, max_length=255)


class UserUpdate(BaseModel):
    """Schema for updating a user"""

    username: str | None = Field(None, min_length=3, max_length=255)
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8, max_length=255)
    is_active: bool | None = None
    is_verified: bool | None = None


class UserInDB(UserBase):
    """Schema for user in database"""

    id: str
    password_hash: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None

    model_config = {"from_attributes": True}


class UserResponse(UserBase):
    """Schema for user response (without sensitive data)"""

    id: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None

    model_config = {"from_attributes": True}


class UserRegister(BaseModel):
    """Schema for user registration"""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(
        ...,
        min_length=3,
        max_length=20,
        description="Username (3-20 characters, alphanumeric, dash, underscore)",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (8-128 characters)",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format: only letters, digits, dash, underscore"""
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Username can only contain letters, numbers, dash, and underscore"
            )
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password requirements"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password must not exceed 128 characters")
        return v


class UserRegistrationResponse(BaseModel):
    """Schema for user registration response"""

    id: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., description="User username")
    created_at: datetime = Field(..., description="User creation timestamp")

    model_config = {"from_attributes": True}
