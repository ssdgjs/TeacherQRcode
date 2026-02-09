"""
Alembic 环境配置
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).resolve().parent.parent))

# 导入模型
from sqlmodel import SQLModel
from models import User, HomeworkItem
from database import DATABASE_URL

# Alembic Config 对象
config = context.config

# 从环境变量读取数据库连接
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# 解析日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 模型的元数据
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """
    离线模式运行迁移（生成SQL脚本）
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    在线模式运行迁移（直接连接数据库）
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# 根据上下文判断运行模式
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
