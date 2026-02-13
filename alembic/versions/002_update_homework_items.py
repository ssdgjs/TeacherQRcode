"""
更新作业表：添加用户关联和AI生成相关字段

Revision ID: 002
Revises: 001
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """更新 homework_items 表"""
    # 添加用户关联字段
    op.add_column('homework_items', sa.Column('user_id', sa.Integer(), nullable=True))

    # 添加AI生成相关字段
    op.add_column('homework_items', sa.Column('grade', sa.String(length=50), nullable=True))
    op.add_column('homework_items', sa.Column('topic', sa.String(length=100), nullable=True))
    op.add_column('homework_items', sa.Column('difficulty', sa.String(length=20), nullable=True))
    op.add_column('homework_items', sa.Column('question_types', sa.String(length=100), nullable=True))

    # 创建外键约束
    op.create_foreign_key(
        'fk_homework_items_user_id',
        'homework_items', 'users',
        ['user_id'], ['id']
    )


def downgrade() -> None:
    """回滚更新"""
    op.drop_constraint('fk_homework_items_user_id', 'homework_items', type_='foreignkey')
    op.drop_column('homework_items', 'question_types')
    op.drop_column('homework_items', 'difficulty')
    op.drop_column('homework_items', 'topic')
    op.drop_column('homework_items', 'grade')
    op.drop_column('homework_items', 'user_id')
