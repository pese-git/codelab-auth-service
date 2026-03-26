"""Session management service"""

from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import logger
from app.models.refresh_token import RefreshToken


class SessionService:
    """Service for managing user sessions"""

    async def list_user_sessions(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> list[dict]:
        """
        Get list of all active sessions for a user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            List of session info dicts
        """
        result = await db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked == False,
                )
            )
        )
        
        tokens = result.scalars().all()
        
        # Group by session_id, keep the latest for each
        sessions_map = {}
        for token in tokens:
            if token.session_id not in sessions_map:
                sessions_map[token.session_id] = token
            elif token.created_at > sessions_map[token.session_id].created_at:
                sessions_map[token.session_id] = token
        
        sessions = []
        for session_id, token in sessions_map.items():
            sessions.append({
                "session_id": session_id,
                "client_id": token.client_id,
                "created_at": token.created_at,
                "last_used": token.last_used,
                "ip_address": token.ip_address,
                "user_agent": token.user_agent,
                "expires_at": token.expires_at,
            })
        
        return sorted(sessions, key=lambda x: x["created_at"], reverse=True)

    async def get_session_info(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: str,
    ) -> dict | None:
        """
        Get detailed information about a specific session
        
        Args:
            db: Database session
            user_id: User ID
            session_id: Session ID
            
        Returns:
            Session info dict or None if not found/revoked
        """
        result = await db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.session_id == session_id,
                    RefreshToken.revoked == False,
                )
            )
        )
        
        token = result.scalars().first()
        if not token:
            return None
        
        return {
            "session_id": token.session_id,
            "client_id": token.client_id,
            "scope": token.scope,
            "created_at": token.created_at,
            "last_used": token.last_used,
            "last_rotated_at": token.last_rotated_at,
            "ip_address": token.ip_address,
            "user_agent": token.user_agent,
            "expires_at": token.expires_at,
        }

    async def revoke_session(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: str,
    ) -> bool:
        """
        Revoke a specific session (all its tokens)
        
        Args:
            db: Database session
            user_id: User ID
            session_id: Session ID to revoke
            
        Returns:
            True if session was revoked, False if not found
        """
        result = await db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.session_id == session_id,
                    RefreshToken.revoked == False,
                )
            )
        )
        
        tokens = result.scalars().all()
        if not tokens:
            return False
        
        revoked_count = 0
        for token in tokens:
            token.revoked = True
            token.revoked_at = datetime.now(timezone.utc)
            revoked_count += 1
        
        await db.commit()
        
        logger.info(
            f"Revoked session {session_id} for user {user_id} "
            f"({revoked_count} tokens)"
        )
        
        return True

    async def revoke_all_sessions(
        self,
        db: AsyncSession,
        user_id: str,
        except_session_id: str | None = None,
    ) -> int:
        """
        Revoke all user sessions except optionally one
        
        Args:
            db: Database session
            user_id: User ID
            except_session_id: Session ID to keep active (optional)
            
        Returns:
            Number of revoked tokens
        """
        query = select(RefreshToken).where(
            and_(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False,
            )
        )
        
        result = await db.execute(query)
        tokens = result.scalars().all()
        
        revoked_count = 0
        now = datetime.now(timezone.utc)
        
        for token in tokens:
            # Skip the exception session if specified
            if except_session_id and token.session_id == except_session_id:
                continue
            
            token.revoked = True
            token.revoked_at = now
            revoked_count += 1
        
        if revoked_count > 0:
            await db.commit()
            
            except_info = f" (except {except_session_id})" if except_session_id else ""
            logger.info(
                f"Revoked all sessions for user {user_id}{except_info} "
                f"({revoked_count} tokens)"
            )
        
        return revoked_count

    async def get_active_sessions_count(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> int:
        """
        Get count of active sessions for a user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Count of active sessions
        """
        sessions = await self.list_user_sessions(db, user_id)
        return len(sessions)


# Global instance
session_service = SessionService()
