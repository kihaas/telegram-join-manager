"""Initial migration - preserve existing data from applications.db

Revision ID: 0001
Revises:
Create Date: 2026-01-15 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op  # type: ignore
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Создаём новые таблицы для расширенного функционала.

    Таблицы users и admin уже существуют в старой БД,
    поэтому мы их НЕ создаём заново, а только добавляем новые таблицы.
    """

    # === Таблица заявок на вступление ===
    op.create_table(
        'pending_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('request_time', sa.DateTime(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'DECLINED', 'BANNED', name='requeststatus'), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('processed_by', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_status_time', 'pending_requests', ['status', 'request_time'])
    op.create_index(op.f('ix_pending_requests_request_time'), 'pending_requests', ['request_time'])
    op.create_index(op.f('ix_pending_requests_status'), 'pending_requests', ['status'])
    op.create_index(op.f('ix_pending_requests_user_id'), 'pending_requests', ['user_id'])

    # === Таблица вариантов капчи ===
    op.create_table(
        'captcha_variants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.Enum('EMOJI', 'IMAGE', 'MATH', name='captchatype'), nullable=False),
        sa.Column('content', sa.String(length=255), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_type_group', 'captcha_variants', ['type', 'group_id'])
    op.create_index(op.f('ix_captcha_variants_type'), 'captcha_variants', ['type'])

    # === Таблица черновиков рассылок ===
    op.create_table(
        'broadcast_drafts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('media_id', sa.String(length=255), nullable=True),
        sa.Column('buttons', sa.Text(), nullable=False),
        sa.Column('creator_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'SENDING', 'COMPLETED', 'CANCELLED', 'FAILED', name='broadcaststatus'),
                  nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('total_users', sa.Integer(), nullable=False),
        sa.Column('successful_sends', sa.Integer(), nullable=False),
        sa.Column('failed_sends', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_broadcast_drafts_status'), 'broadcast_drafts', ['status'])

    # === Таблица вариантов приветствий ===
    op.create_table(
        'welcome_variants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('media_id', sa.String(length=255), nullable=True),
        sa.Column('buttons', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('weight', sa.Integer(), nullable=False),
        sa.Column('views_count', sa.Integer(), nullable=False),
        sa.Column('agrees_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_welcome_variants_is_active'), 'welcome_variants', ['is_active'])

    # === Таблица попыток капчи ===
    op.create_table(
        'captcha_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('captcha_type', sa.Enum('EMOJI', 'IMAGE', 'MATH', name='captchatype'), nullable=False),
        sa.Column('is_successful', sa.Boolean(), nullable=False),
        sa.Column('attempt_time', sa.DateTime(), nullable=False),
        sa.Column('attempts_count', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_time', 'captcha_attempts', ['user_id', 'attempt_time'])
    op.create_index(op.f('ix_captcha_attempts_attempt_time'), 'captcha_attempts', ['attempt_time'])
    op.create_index(op.f('ix_captcha_attempts_user_id'), 'captcha_attempts', ['user_id'])


def downgrade() -> None:
    """Откат миграции - удаление новых таблиц."""
    op.drop_index(op.f('ix_captcha_attempts_user_id'), table_name='captcha_attempts')
    op.drop_index(op.f('ix_captcha_attempts_attempt_time'), table_name='captcha_attempts')
    op.drop_index('idx_user_time', table_name='captcha_attempts')
    op.drop_table('captcha_attempts')

    op.drop_index(op.f('ix_welcome_variants_is_active'), table_name='welcome_variants')
    op.drop_table('welcome_variants')

    op.drop_index(op.f('ix_broadcast_drafts_status'), table_name='broadcast_drafts')
    op.drop_table('broadcast_drafts')

    op.drop_index(op.f('ix_captcha_variants_type'), table_name='captcha_variants')
    op.drop_index('idx_type_group', table_name='captcha_variants')
    op.drop_table('captcha_variants')

    op.drop_index(op.f('ix_pending_requests_user_id'), table_name='pending_requests')
    op.drop_index(op.f('ix_pending_requests_status'), table_name='pending_requests')
    op.drop_index(op.f('ix_pending_requests_request_time'), table_name='pending_requests')
    op.drop_index('idx_status_time', table_name='pending_requests')
    op.drop_table('pending_requests')