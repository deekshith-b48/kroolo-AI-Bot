"""Admin system tables

Revision ID: 002_admin_system
Revises: 001_initial_schema
Create Date: 2024-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_admin_system'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    """Create admin system tables."""
    
    # Create enum types
    admin_role_enum = postgresql.ENUM('super_admin', 'admin', 'moderator', name='adminrole', create_type=False)
    admin_role_enum.create(op.get_bind())
    
    workflow_status_enum = postgresql.ENUM('pending', 'approved', 'rejected', 'active', 'inactive', name='workflowstatus', create_type=False)
    workflow_status_enum.create(op.get_bind())
    
    audit_action_enum = postgresql.ENUM(
        'user_promoted', 'user_demoted', 'user_banned', 'user_unbanned', 
        'user_muted', 'user_unmuted', 'workflow_added', 'workflow_removed',
        'workflow_enabled', 'workflow_disabled', 'command_enabled', 'command_disabled',
        'topic_created', 'topic_closed', 'bot_reloaded', 'settings_changed',
        name='auditaction', create_type=False
    )
    audit_action_enum.create(op.get_bind())
    
    # Create admin_users table
    op.create_table('admin_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('role', admin_role_enum, nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['admin_users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admin_users_id'), 'admin_users', ['id'], unique=False)
    op.create_index(op.f('ix_admin_users_telegram_user_id'), 'admin_users', ['telegram_user_id'], unique=True)
    
    # Create banned_users table
    op.create_table('banned_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('banned_by_id', sa.Integer(), nullable=False),
        sa.Column('banned_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['banned_by_id'], ['admin_users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_banned_users_id'), 'banned_users', ['id'], unique=False)
    op.create_index(op.f('ix_banned_users_telegram_user_id'), 'banned_users', ['telegram_user_id'], unique=True)
    
    # Create muted_users table
    op.create_table('muted_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('muted_by_id', sa.Integer(), nullable=False),
        sa.Column('muted_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['muted_by_id'], ['admin_users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_muted_users_id'), 'muted_users', ['id'], unique=False)
    op.create_index(op.f('ix_muted_users_telegram_user_id'), 'muted_users', ['telegram_user_id'], unique=False)
    op.create_index(op.f('ix_muted_users_chat_id'), 'muted_users', ['chat_id'], unique=False)
    
    # Create bot_workflows table
    op.create_table('bot_workflows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('trigger_command', sa.String(length=255), nullable=True),
        sa.Column('endpoint_url', sa.String(length=1000), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=True, default='POST'),
        sa.Column('headers', sa.JSON(), nullable=True),
        sa.Column('payload_template', sa.JSON(), nullable=True),
        sa.Column('status', workflow_status_enum, nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('approved_by_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=False),
        sa.Column('execution_count', sa.Integer(), nullable=True, default=0),
        sa.Column('last_executed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['approved_by_id'], ['admin_users.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['admin_users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bot_workflows_id'), 'bot_workflows', ['id'], unique=False)
    op.create_index(op.f('ix_bot_workflows_name'), 'bot_workflows', ['name'], unique=True)
    
    # Create community_settings table
    op.create_table('community_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('chat_title', sa.String(length=255), nullable=True),
        sa.Column('chat_type', sa.String(length=50), nullable=False),
        sa.Column('auto_moderation', sa.Boolean(), nullable=True, default=False),
        sa.Column('auto_topic_creation', sa.Boolean(), nullable=True, default=False),
        sa.Column('manual_approval', sa.Boolean(), nullable=True, default=False),
        sa.Column('allowed_commands', sa.JSON(), nullable=True),
        sa.Column('blocked_commands', sa.JSON(), nullable=True),
        sa.Column('welcome_message', sa.Text(), nullable=True),
        sa.Column('community_rules', sa.Text(), nullable=True),
        sa.Column('default_topic_id', sa.Integer(), nullable=True),
        sa.Column('admin_only_mode', sa.Boolean(), nullable=True, default=False),
        sa.Column('ai_assistant_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('managed_by_id', sa.Integer(), nullable=True),
        sa.Column('settings_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['managed_by_id'], ['admin_users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_community_settings_id'), 'community_settings', ['id'], unique=False)
    op.create_index(op.f('ix_community_settings_chat_id'), 'community_settings', ['chat_id'], unique=True)
    
    # Create pending_approvals table
    op.create_table('pending_approvals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_type', sa.String(length=100), nullable=False),
        sa.Column('request_data', sa.JSON(), nullable=False),
        sa.Column('requested_by_id', sa.BigInteger(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, default='pending'),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('review_message', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['admin_users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pending_approvals_id'), 'pending_approvals', ['id'], unique=False)
    
    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admin_id', sa.Integer(), nullable=False),
        sa.Column('action', audit_action_enum, nullable=False),
        sa.Column('target_user_id', sa.BigInteger(), nullable=True),
        sa.Column('chat_id', sa.BigInteger(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['admin_id'], ['admin_users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_admin_id'), 'audit_logs', ['admin_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)


def downgrade():
    """Drop admin system tables."""
    
    # Drop tables in reverse order
    op.drop_table('audit_logs')
    op.drop_table('pending_approvals')
    op.drop_table('community_settings')
    op.drop_table('bot_workflows')
    op.drop_table('muted_users')
    op.drop_table('banned_users')
    op.drop_table('admin_users')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS auditaction')
    op.execute('DROP TYPE IF EXISTS workflowstatus')
    op.execute('DROP TYPE IF EXISTS adminrole')
