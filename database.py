"""
PostgreSQL 数据库连接配置
"""
import os
from sqlmodel import create_engine, Session
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    database_url: str = "postgresql://eduqr:eduqr_password@localhost:5432/eduqr"

    class Config:
        env_file = ".env"
        extra = "ignore"  # 忽略额外的环境变量
        # 不使用 env_prefix，直接读取 DATABASE_URL


# 使用环境变量或默认值
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://eduqr:eduqr_password@localhost:5432/eduqr"
)

# 创建数据库引擎
if DATABASE_URL.startswith("sqlite"):
    # SQLite 配置
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL 配置
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # 设置为True可以看到SQL日志
        pool_pre_ping=True,  # 检查连接有效性
        pool_size=5,  # 连接池大小
        max_overflow=10  # 最大溢出连接数
    )


def init_db():
    """初始化数据库表"""
    from sqlmodel import SQLModel
    from models import User, HomeworkItem  # 导入所有模型

    SQLModel.metadata.create_all(engine)
    db_type = "SQLite" if DATABASE_URL.startswith("sqlite") else "PostgreSQL"
    print(f"✅ {db_type} database initialized at: {DATABASE_URL}")


def get_session():
    """获取数据库会话"""
    with Session(engine) as session:
        yield session


def check_db_connection():
    """检查数据库连接"""
    try:
        with Session(engine) as session:
            session.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
