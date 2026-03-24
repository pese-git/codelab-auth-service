"""add_password_reset_tokens

Revision ID: 8cd3d4e5f6bg
Revises: 7bc2c3d4e5af
Create Date: 2026-03-24 16:45:00.000000

Adds password_reset_tokens table for managing password reset flows.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8cd3d4e5f6bg'
down_revision: Union[str, None] = '7bc2c3d4e5af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create password_reset_tokens table
    op.create_table('password_reset_tokens',
    sa.Column('id', sa.VARCHAR(length=36), nullable=False),
    sa.Column('user_id', sa.VARCHAR(length=36), nullable=False),
    sa.Column('token_hash', sa.VARCHAR(length=64), nullable=False),
    sa.Column('created_at', sa.DATETIME(), nullable=False),
    sa.Column('expires_at', sa.DATETIME(), nullable=False),
    sa.Column('used_at', sa.DATETIME(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_password_reset_tokens_token_hash', 'password_reset_tokens', ['token_hash'], unique=True)
    op.create_index('ix_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id'])
    op.create_index('ix_password_reset_tokens_expires_at', 'password_reset_tokens', ['expires_at'])


def downgrade() -> None:
    op.drop_index('ix_password_reset_tokens_expires_at', table_name='password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_user_id', table_name='password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_token_hash', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
