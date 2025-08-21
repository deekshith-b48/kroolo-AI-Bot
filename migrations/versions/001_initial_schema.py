"""Initial database schema with Phase 5 tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all initial database tables."""
    
    # Create agents table
    op.create_table(
        'agents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('handle', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('persona_prompt', sa.Text(), nullable=False),
        sa.Column('capabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('guardrails', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('agent_type', sa.String(length=50), nullable=True),
        sa.Column('version', sa.String(length=20), nullable=True),
        sa.Column('max_tokens_per_response', sa.Integer(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('model_name', sa.String(length=100), nullable=True),
        sa.Column('rate_limits', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('handle')
    )
    op.create_index(op.f('ix_agents_handle'), 'agents', ['handle'], unique=False)
    
    # Create chat_configs table
    op.create_table(
        'chat_configs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('enabled_agents', postgresql.ARRAY(sa.UUID()), nullable=True),
        sa.Column('default_agent', sa.UUID(), nullable=True),
        sa.Column('schedules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('moderation_policy', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('feature_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('chat_type', sa.String(length=20), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=True),
        sa.Column('welcome_message', sa.Text(), nullable=True),
        sa.Column('admin_users', postgresql.ARRAY(sa.BigInteger()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['default_agent'], ['agents.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_id')
    )
    op.create_index(op.f('ix_chat_configs_chat_id'), 'chat_configs', ['chat_id'], unique=False)
    
    # Create message_logs table
    op.create_table(
        'message_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('update_id', sa.BigInteger(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('normalized_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('handled_by', sa.String(length=100), nullable=True),
        sa.Column('result_msg_id', sa.BigInteger(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('message_type', sa.String(length=50), nullable=True),
        sa.Column('intent_detected', sa.String(length=50), nullable=True),
        sa.Column('route_reason', sa.String(length=200), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('agent_response_time', sa.Integer(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('cost_cents', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['chat_id'], ['chat_configs.chat_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_message_logs_chat_id'), 'message_logs', ['chat_id'], unique=False)
    op.create_index(op.f('ix_message_logs_update_id'), 'message_logs', ['update_id'], unique=False)
    op.create_index(op.f('ix_message_logs_user_id'), 'message_logs', ['user_id'], unique=False)
    
    # Create schedules table
    op.create_table(
        'schedules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('task_type', sa.String(length=100), nullable=False),
        sa.Column('cron_expr', sa.String(length=100), nullable=True),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('schedule_type', sa.String(length=50), nullable=True),
        sa.Column('schedule_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('content_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('next_run', sa.TIMESTAMP(), nullable=True),
        sa.Column('last_run', sa.TIMESTAMP(), nullable=True),
        sa.Column('run_count', sa.Integer(), nullable=True),
        sa.Column('max_runs', sa.Integer(), nullable=True),
        sa.Column('failure_count', sa.Integer(), nullable=True),
        sa.Column('max_failures', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['chat_id'], ['chat_configs.chat_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_schedules_chat_id'), 'schedules', ['chat_id'], unique=False)
    
    # Create quizzes table
    op.create_table(
        'quizzes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('answer_idx', sa.Integer(), nullable=False),
        sa.Column('start_ts', sa.TIMESTAMP(), nullable=True),
        sa.Column('end_ts', sa.TIMESTAMP(), nullable=True),
        sa.Column('results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('difficulty', sa.String(length=20), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('time_limit_seconds', sa.Integer(), nullable=True),
        sa.Column('max_participants', sa.Integer(), nullable=True),
        sa.Column('created_by_user', sa.BigInteger(), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quizzes_chat_id'), 'quizzes', ['chat_id'], unique=False)
    
    # Create quiz_attempts table
    op.create_table(
        'quiz_attempts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('quiz_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('selected_answer', sa.Integer(), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('attempt_number', sa.Integer(), nullable=True),
        sa.Column('hints_used', sa.Integer(), nullable=True),
        sa.Column('submitted_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_attempts_chat_id'), 'quiz_attempts', ['chat_id'], unique=False)
    op.create_index(op.f('ix_quiz_attempts_user_id'), 'quiz_attempts', ['user_id'], unique=False)
    
    # Create news_articles table
    op.create_table(
        'news_articles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('url', sa.String(length=1000), nullable=True),
        sa.Column('source', sa.String(length=200), nullable=False),
        sa.Column('author', sa.String(length=200), nullable=True),
        sa.Column('published_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('sentiment', sa.String(length=20), nullable=True),
        sa.Column('keywords', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('ai_summary', sa.Text(), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('reading_time_minutes', sa.Integer(), nullable=True),
        sa.Column('image_urls', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create debates table
    op.create_table(
        'debates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('topic', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('participants', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('max_turns', sa.Integer(), nullable=True),
        sa.Column('current_turn', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('time_limit_minutes', sa.Integer(), nullable=True),
        sa.Column('audience_voting', sa.Boolean(), nullable=True),
        sa.Column('moderated', sa.Boolean(), nullable=True),
        sa.Column('winner', sa.String(length=100), nullable=True),
        sa.Column('audience_votes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('final_scores', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_debates_chat_id'), 'debates', ['chat_id'], unique=False)
    
    # Create debate_messages table
    op.create_table(
        'debate_messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('debate_id', sa.UUID(), nullable=False),
        sa.Column('participant', sa.String(length=100), nullable=False),
        sa.Column('turn_number', sa.Integer(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('position', sa.String(length=20), nullable=True),
        sa.Column('argument_strength', sa.Float(), nullable=True),
        sa.Column('sentiment', sa.String(length=20), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('response_to_message_id', sa.UUID(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['debate_id'], ['debates.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create fun_content table
    op.create_table(
        'fun_content',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('difficulty', sa.String(length=20), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('source', sa.String(length=200), nullable=True),
        sa.Column('author', sa.String(length=200), nullable=True),
        sa.Column('likes', sa.Integer(), nullable=True),
        sa.Column('dislikes', sa.Integer(), nullable=True),
        sa.Column('shares', sa.Integer(), nullable=True),
        sa.Column('last_used', sa.TIMESTAMP(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create knowledge_documents table
    op.create_table(
        'knowledge_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('doc_id', sa.String(length=200), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('content_type', sa.String(length=50), nullable=True),
        sa.Column('chunk_count', sa.Integer(), nullable=True),
        sa.Column('embedding_model', sa.String(length=100), nullable=True),
        sa.Column('processing_status', sa.String(length=50), nullable=True),
        sa.Column('access_level', sa.String(length=20), nullable=True),
        sa.Column('owner_user_id', sa.BigInteger(), nullable=True),
        sa.Column('filename', sa.String(length=500), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('doc_id')
    )
    op.create_index(op.f('ix_knowledge_documents_chat_id'), 'knowledge_documents', ['chat_id'], unique=False)
    op.create_index(op.f('ix_knowledge_documents_doc_id'), 'knowledge_documents', ['doc_id'], unique=False)
    
    # Create user_profiles table
    op.create_table(
        'user_profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('first_name', sa.String(length=200), nullable=True),
        sa.Column('last_name', sa.String(length=200), nullable=True),
        sa.Column('language_code', sa.String(length=10), nullable=True),
        sa.Column('preferred_agents', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('notification_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('privacy_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('total_messages', sa.Integer(), nullable=True),
        sa.Column('total_quiz_attempts', sa.Integer(), nullable=True),
        sa.Column('total_debates_participated', sa.Integer(), nullable=True),
        sa.Column('favorite_content_types', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('last_active', sa.TIMESTAMP(), nullable=True),
        sa.Column('streak_days', sa.Integer(), nullable=True),
        sa.Column('points', sa.Integer(), nullable=True),
        sa.Column('level', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_user_profiles_user_id'), 'user_profiles', ['user_id'], unique=False)
    
    # Create feature_flags table (additional table for granular feature control)
    op.create_table(
        'feature_flags',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('feature', sa.String(length=100), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('updated_by', sa.BigInteger(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rollout_percentage', sa.Integer(), default=100),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_feature_flags_chat_id'), 'feature_flags', ['chat_id'], unique=False)
    op.create_index(op.f('ix_feature_flags_feature'), 'feature_flags', ['feature'], unique=False)
    
    # Create agent_prompts table (for versioned prompts)
    op.create_table(
        'agent_prompts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('agent_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False),
        sa.Column('prompt_text', sa.Text(), nullable=False),
        sa.Column('active', sa.Boolean(), default=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('performance_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_prompts_agent_id'), 'agent_prompts', ['agent_id'], unique=False)
    
    # Create system_metrics table (for storing metrics history)
    op.create_table(
        'system_metrics',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('metric_type', sa.String(length=50), nullable=False),  # counter, gauge, histogram
        sa.Column('labels', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=False),
        sa.Column('service_name', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_metrics_metric_name'), 'system_metrics', ['metric_name'], unique=False)
    op.create_index(op.f('ix_system_metrics_timestamp'), 'system_metrics', ['timestamp'], unique=False)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('system_metrics')
    op.drop_table('agent_prompts')
    op.drop_table('feature_flags')
    op.drop_table('user_profiles')
    op.drop_table('knowledge_documents')
    op.drop_table('fun_content')
    op.drop_table('debate_messages')
    op.drop_table('debates')
    op.drop_table('quiz_attempts')
    op.drop_table('quizzes')
    op.drop_table('schedules')
    op.drop_table('message_logs')
    op.drop_table('chat_configs')
    op.drop_table('agents')
