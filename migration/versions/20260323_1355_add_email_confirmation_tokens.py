"""add_email_confirmation_tokens

Revision ID: 7bc2c3d4e5af
Revises: 5ab1b2b376af
Create Date: 2026-03-23 13:55:00.000000

Adds email_confirmation_tokens table for managing email confirmation flows.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7bc2c3d4e5af'
down_revision: Union[str, None] = '5ab1b2b376af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create email_confirmation_tokens table
    op.create_table('email_confirmation_tokens',
    sa.Column('id', sa.VARCHAR(length=36), nullable=False),
    sa.Column('user_id', sa.VARCHAR(length=36), nullable=False),
    sa.Column('token', sa.VARCHAR(length=255), nullable=False),
    sa.Column('expires_at', sa.DATETIME(), nullable=False),
    sa.Column('created_at', sa.DATETIME(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_email_confirmation_tokens_token', 'email_confirmation_tokens', ['token'], unique=True)
    op.create_index('ix_email_confirmation_tokens_user_id', 'email_confirmation_tokens', ['user_id'])
    op.create_index('ix_email_confirmation_tokens_expires_at', 'email_confirmation_tokens', ['expires_at'])


def downgrade() -> None:
    op.drop_index('ix_email_confirmation_tokens_expires_at', table_name='email_confirmation_tokens')
    op.drop_index('ix_email_confirmation_tokens_user_id', table_name='email_confirmation_tokens')
    op.drop_index('ix_email_confirmation_tokens_token', table_name='email_confirmation_tokens')
    op.drop_table('email_confirmation_tokens')
