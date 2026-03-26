"""add_session_management

Revision ID: 9de4e5f6g7ch
Revises: 8cd3d4e5f6bg
Create Date: 2026-03-25 14:47:00.000000

Adds session management columns and metadata to refresh_tokens table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9de4e5f6g7ch'
down_revision: Union[str, None] = '8cd3d4e5f6bg'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add session management columns to refresh_tokens table"""
    
    # Add session_id column
    op.add_column('refresh_tokens',
        sa.Column('session_id', sa.VARCHAR(length=36), nullable=False, server_default=sa.func.uuid())
    )
    
    # Add last_used column
    op.add_column('refresh_tokens',
        sa.Column('last_used', sa.DATETIME(timezone=True), nullable=True)
    )
    
    # Add last_rotated_at column
    op.add_column('refresh_tokens',
        sa.Column('last_rotated_at', sa.DATETIME(timezone=True), nullable=True)
    )
    
    # Add ip_address column
    op.add_column('refresh_tokens',
        sa.Column('ip_address', sa.VARCHAR(length=45), nullable=True)
    )
    
    # Add user_agent column
    op.add_column('refresh_tokens',
        sa.Column('user_agent', sa.VARCHAR(length=500), nullable=True)
    )
    
    # Create index on session_id
    op.create_index('ix_refresh_tokens_session_id', 'refresh_tokens', ['session_id'])
    
    # Create compound index on user_id, client_id, revoked for session queries
    op.create_index('ix_refresh_tokens_user_client_revoked', 'refresh_tokens', 
                   ['user_id', 'client_id', 'revoked'])


def downgrade() -> None:
    """Revert session management columns from refresh_tokens table"""
    
    # Drop indexes
    op.drop_index('ix_refresh_tokens_user_client_revoked', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_session_id', table_name='refresh_tokens')
    
    # Drop columns
    op.drop_column('refresh_tokens', 'user_agent')
    op.drop_column('refresh_tokens', 'ip_address')
    op.drop_column('refresh_tokens', 'last_rotated_at')
    op.drop_column('refresh_tokens', 'last_used')
    op.drop_column('refresh_tokens', 'session_id')
