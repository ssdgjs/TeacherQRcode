"""
创建额度表

Revision ID: 003
Revises: 002
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建 quotas 表"""
    op.create_table(
        'quotas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('free_used_today', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('free_reset_date', sa.DateTime(), nullable=True),
        sa.Column('purchased_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('subscription_expires_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quotas_user_id'), 'quotas', ['user_id'], unique=True)
    op.create_index(op.f('ix_quotas_id'), 'quotas', ['id'], unique=False)

    # 创建外键约束
    op.create_foreign_key(
        'fk_quotas_user_id',
        'quotas', 'users',
        ['user_id'], ['id']
    )


def downgrade() -> None:
    """删除 quotas 表"""
    op.drop_constraint('fk_quotas_user_id', 'quotas', type_='foreignkey')
    op.drop_index(op.f('ix_quotas_id'), table_name='quotas')
    op.drop_index(op.f('ix_quotas_user_id'), table_name='quotas')
    op.drop_table('quotas')
