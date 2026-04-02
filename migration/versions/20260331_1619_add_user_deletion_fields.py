"""add_user_deletion_fields

Revision ID: 0ae5f7g8h9di
Revises: 9de4e5f6g7ch
Create Date: 2026-03-31 16:19:00.000000

Adds soft delete fields to users table for event-driven user synchronization.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0ae5f7g8h9di'
down_revision: Union[str, None] = '9de4e5f6g7ch'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add soft delete fields to users table"""
    
    # Add is_deleted column
    op.add_column('users',
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0')
    )
    
    # Add deleted_at column
    op.add_column('users',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )
    
    # Add deletion_reason column
    op.add_column('users',
        sa.Column('deletion_reason', sa.VARCHAR(length=255), nullable=True)
    )
    
    # Create index on is_deleted and deleted_at for queries
    op.create_index('ix_users_is_deleted_deleted_at', 'users', 
                   ['is_deleted', 'deleted_at'])


def downgrade() -> None:
    """Revert soft delete fields from users table"""
    
    # Drop index
    op.drop_index('ix_users_is_deleted_deleted_at', table_name='users')
    
    # Drop columns
    op.drop_column('users', 'deletion_reason')
    op.drop_column('users', 'deleted_at')
    op.drop_column('users', 'is_deleted')
