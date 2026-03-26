"""Session management schemas"""

from datetime import datetime

from pydantic import BaseModel, Field


class SessionInfo(BaseModel):
    """Session information"""

    session_id: str = Field(..., description="Unique session identifier")
    client_id: str = Field(..., description="OAuth client ID")
    created_at: str = Field(..., description="Session creation timestamp (ISO 8601)")
    last_used: str | None = Field(None, description="Last usage timestamp (ISO 8601)")
    ip_address: str | None = Field(None, description="Client IP address")
    user_agent: str | None = Field(None, description="Client User-Agent")
    expires_at: str = Field(..., description="Token expiration timestamp (ISO 8601)")


class ListSessionsResponse(BaseModel):
    """Response for listing user sessions"""

    sessions: list[SessionInfo] = Field(..., description="List of active sessions")


class GetSessionResponse(BaseModel):
    """Response for getting session details"""

    session_id: str = Field(..., description="Unique session identifier")
    client_id: str = Field(..., description="OAuth client ID")
    scope: str | None = Field(None, description="Granted scopes")
    created_at: str = Field(..., description="Session creation timestamp (ISO 8601)")
    last_used: str | None = Field(None, description="Last usage timestamp (ISO 8601)")
    last_rotated_at: str | None = Field(None, description="Last rotation timestamp (ISO 8601)")
    ip_address: str | None = Field(None, description="Client IP address")
    user_agent: str | None = Field(None, description="Client User-Agent")
    expires_at: str = Field(..., description="Token expiration timestamp (ISO 8601)")


class RevokeSessionResponse(BaseModel):
    """Response for session revocation"""

    message: str = Field(..., description="Operation result message")
    session_id: str | None = Field(None, description="Revoked session ID")
