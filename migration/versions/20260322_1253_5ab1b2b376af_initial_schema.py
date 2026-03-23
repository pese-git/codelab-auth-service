"""initial_schema

Revision ID: 5ab1b2b376af
Revises: 
Create Date: 2026-03-22 12:53:06.101816

Creates initial database schema with all core tables:
- users: User accounts with authentication
- oauth_clients: OAuth2 client applications
- refresh_tokens: Token rotation and management
- audit_logs: Security event logging
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '5ab1b2b376af'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
    sa.Column('id', sa.VARCHAR(length=36), nullable=False),
    sa.Column('username', sa.VARCHAR(length=255), nullable=False),
    sa.Column('email', sa.VARCHAR(length=255), nullable=False),
    sa.Column('password_hash', sa.VARCHAR(length=255), nullable=False),
    sa.Column('is_active', sa.BOOLEAN(), nullable=False),
    sa.Column('is_verified', sa.BOOLEAN(), nullable=False),
    sa.Column('email_confirmed', sa.BOOLEAN(), nullable=False),
    sa.Column('created_at', sa.DATETIME(), nullable=False),
    sa.Column('updated_at', sa.DATETIME(), nullable=False),
    sa.Column('last_login_at', sa.DATETIME(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_is_active', 'users', ['is_active'])
    
    # Create oauth_clients table
    op.create_table('oauth_clients',
    sa.Column('id', sa.VARCHAR(length=36), nullable=False),
    sa.Column('client_id', sa.VARCHAR(length=255), nullable=False),
    sa.Column('client_secret_hash', sa.VARCHAR(length=255), nullable=True),
    sa.Column('name', sa.VARCHAR(length=255), nullable=False),
    sa.Column('description', sa.TEXT(), nullable=True),
    sa.Column('is_confidential', sa.BOOLEAN(), nullable=False),
    sa.Column('allowed_scopes', sa.TEXT(), nullable=False),
    sa.Column('allowed_grant_types', sa.TEXT(), nullable=False),
    sa.Column('access_token_lifetime', sa.INTEGER(), nullable=False),
    sa.Column('refresh_token_lifetime', sa.INTEGER(), nullable=False),
    sa.Column('is_active', sa.BOOLEAN(), nullable=False),
    sa.Column('created_at', sa.DATETIME(), nullable=False),
    sa.Column('updated_at', sa.DATETIME(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_oauth_clients_client_id', 'oauth_clients', ['client_id'], unique=True)
    op.create_index('ix_oauth_clients_is_active', 'oauth_clients', ['is_active'])
    
    # Create refresh_tokens table
    op.create_table('refresh_tokens',
    sa.Column('id', sa.VARCHAR(length=36), nullable=False),
    sa.Column('jti_hash', sa.VARCHAR(length=64), nullable=False),
    sa.Column('user_id', sa.VARCHAR(length=36), nullable=False),
    sa.Column('client_id', sa.VARCHAR(length=255), nullable=False),
    sa.Column('scope', sa.TEXT(), nullable=False),
    sa.Column('expires_at', sa.DATETIME(), nullable=False),
    sa.Column('revoked', sa.BOOLEAN(), nullable=False),
    sa.Column('revoked_at', sa.DATETIME(), nullable=True),
    sa.Column('parent_jti_hash', sa.VARCHAR(length=64), nullable=True),
    sa.Column('created_at', sa.DATETIME(), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['oauth_clients.client_id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_refresh_tokens_jti_hash', 'refresh_tokens', ['jti_hash'], unique=True)
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])
    op.create_index('ix_refresh_tokens_client_id', 'refresh_tokens', ['client_id'])
    op.create_index('ix_refresh_tokens_expires_at', 'refresh_tokens', ['expires_at'])
    op.create_index('ix_refresh_tokens_revoked', 'refresh_tokens', ['revoked'])
    
    # Create audit_logs table
    op.create_table('audit_logs',
    sa.Column('id', sa.VARCHAR(length=36), nullable=False),
    sa.Column('user_id', sa.VARCHAR(length=36), nullable=True),
    sa.Column('client_id', sa.VARCHAR(length=255), nullable=True),
    sa.Column('event_type', sa.VARCHAR(length=50), nullable=False),
    sa.Column('event_data', sqlite.JSON(), nullable=True),
    sa.Column('ip_address', sa.VARCHAR(length=45), nullable=True),
    sa.Column('user_agent', sa.TEXT(), nullable=True),
    sa.Column('success', sa.BOOLEAN(), nullable=False),
    sa.Column('error_message', sa.TEXT(), nullable=True),
    sa.Column('created_at', sa.DATETIME(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('ix_audit_logs_success', 'audit_logs', ['success'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])


def downgrade() -> None:
    # Drop audit_logs table
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_success', table_name='audit_logs')
    op.drop_index('ix_audit_logs_event_type', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')
    op.drop_table('audit_logs')
    
    # Drop refresh_tokens table
    op.drop_index('ix_refresh_tokens_revoked', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_expires_at', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_client_id', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_user_id', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_jti_hash', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    
    # Drop oauth_clients table
    op.drop_index('ix_oauth_clients_is_active', table_name='oauth_clients')
    op.drop_index('ix_oauth_clients_client_id', table_name='oauth_clients')
    op.drop_table('oauth_clients')
    
    # Drop users table
    op.drop_index('ix_users_is_active', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_table('users')
