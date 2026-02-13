"""
Pytest配置和共享fixtures
"""
# 设置测试环境变量（必须在所有其他导入之前）
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test_secret_key_at_least_32_chars_long_for_testing"

import tempfile
from pathlib import Path
from typing import Generator

import pytest
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import pool
from fastapi.testclient import TestClient

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock init_db 并覆盖 database engine
import unittest.mock

# 创建测试引擎
test_engine = None

def mock_init_db():
    """Mock init_db 不做任何事"""
    pass

# 在导入main之前应用mock
with unittest.mock.patch('models.init_db', side_effect=mock_init_db):
    # 导入main和database模块
    import database
    import models
    from main import app

    # 创建测试引擎并覆盖
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=pool.StaticPool
    )

    # 覆盖database.engine
    database.engine = test_engine

    # 也要覆盖models中的engine引用（如果有）
    if hasattr(models, 'engine'):
        models.engine = test_engine
from models import User, Quota, HomeworkItem, Order
from auth import get_password_hash, create_access_token


# ==================== 测试数据库配置 ====================
@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """
    创建测试数据库会话

    每个测试函数都有独立的数据库
    """
    # 使用SQLite内存数据库进行测试
    test_db_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
    test_db_url = f"sqlite:///{test_db_file.name}"

    engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
        poolclass=pool.StaticPool
    )

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    # 清理
    SQLModel.metadata.drop_all(engine)
    engine.dispose()
    test_db_file.close()
    os.unlink(test_db_file.name)


@pytest.fixture
def test_client(test_db: Session) -> Generator[TestClient, None, None]:
    """
    创建测试客户端

    依赖test_db fixture
    """
    from database import get_session, engine
    import models

    # 保存原始 engine
    original_engine = engine

    # 获取 test_db 使用的 engine
    test_engine = test_db.bind

    # 覆盖全局 engine
    database.engine = test_engine
    if hasattr(models, 'engine'):
        models.engine = test_engine

    def override_get_session():
        yield test_db

    from main import app
    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as client:
        yield client

    # 恢复原始 engine
    database.engine = original_engine
    if hasattr(models, 'engine'):
        models.engine = original_engine

    app.dependency_overrides.clear()


# ==================== 用户fixtures ====================
@pytest.fixture
def test_user(test_db: Session) -> User:
    """创建测试用户"""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("password123")
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_user_with_quota(test_db: Session) -> User:
    """创建带额度的测试用户"""
    user = User(
        email="user_with_quota@example.com",
        password_hash=get_password_hash("password123")
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    # 创建额度记录
    quota = Quota(
        user_id=user.id,
        free_used_today=0,
        purchased_count=50,
        subscription_expires_at=None
    )
    test_db.add(quota)
    test_db.commit()

    return user


@pytest.fixture
def test_subscriber(test_db: Session) -> User:
    """创建订阅用户"""
    from datetime import datetime, timedelta

    user = User(
        email="subscriber@example.com",
        password_hash=get_password_hash("password123")
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    # 创建订阅额度
    quota = Quota(
        user_id=user.id,
        free_used_today=0,
        purchased_count=0,
        subscription_expires_at=datetime.now() + timedelta(days=30)
    )
    test_db.add(quota)
    test_db.commit()

    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """创建认证头"""
    token = create_access_token({"sub": test_user.id, "email": test_user.email})
    return {"Authorization": f"Bearer {token}"}


# ==================== 作业fixtures ====================
@pytest.fixture
def test_homework(test_db: Session, test_user: User) -> HomeworkItem:
    """创建测试作业"""
    import json
    from utils import generate_short_id

    homework = HomeworkItem(
        user_id=test_user.id,
        short_id=generate_short_id(8),
        content="# Test Homework\n\nThis is a test.",
        title="Test Homework",
        homework_type="text",
        grade="初中二年级",
        topic="现在完成时",
        difficulty="medium",
        question_types=json.dumps([{"type": "choice", "count": 5}])
    )
    test_db.add(homework)
    test_db.commit()
    test_db.refresh(homework)
    return homework


@pytest.fixture
def test_ai_homework(test_db: Session, test_user: User) -> HomeworkItem:
    """创建AI生成的测试作业"""
    import json
    from utils import generate_short_id

    content = {
        "id": "hw_test123",
        "grade": "初中二年级",
        "topic": "现在完成时",
        "difficulty": "medium",
        "questions": [
            {
                "type": "choice",
                "questions": [
                    {
                        "question": "Test question?",
                        "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"],
                        "answer": "A",
                        "explanation": "Test explanation"
                    }
                ]
            }
        ]
    }

    homework = HomeworkItem(
        user_id=test_user.id,
        short_id=generate_short_id(8),
        content=json.dumps(content, ensure_ascii=False),
        title="初中二年级 - 现在完成时",
        homework_type="ai_generated",
        grade="初中二年级",
        topic="现在完成时",
        difficulty="medium",
        question_types=json.dumps([{"type": "choice", "count": 5}])
    )
    test_db.add(homework)
    test_db.commit()
    test_db.refresh(homework)
    return homework


# ==================== 订单fixtures ====================
@pytest.fixture
def test_order(test_db: Session, test_user: User) -> Order:
    """创建测试订单"""
    from payment_service import generate_order_no

    order = Order(
        user_id=test_user.id,
        order_no=generate_order_no(),
        type="package",
        amount=990,
        status="pending"
    )
    test_db.add(order)
    test_db.commit()
    test_db.refresh(order)
    return order


@pytest.fixture
def test_paid_order(test_db: Session, test_user: User) -> Order:
    """创建已支付订单"""
    from payment_service import generate_order_no
    from datetime import datetime

    order = Order(
        user_id=test_user.id,
        order_no=generate_order_no(),
        type="package",
        amount=990,
        status="paid",
        wechat_prepay_id="wx_prepay_id_123",
        paid_at=datetime.now()
    )
    test_db.add(order)
    test_db.commit()
    test_db.refresh(order)

    # 添加额度
    quota = test_db.exec(
        select(Quota).where(Quota.user_id == test_user.id)
    ).first()
    if quota:
        quota.purchased_count += 100
    else:
        quota = Quota(
            user_id=test_user.id,
            purchased_count=100
        )
        test_db.add(quota)
    test_db.commit()

    return order


# ==================== Mock fixtures ====================
@pytest.fixture
def mock_zhipuai_response():
    """Mock智谱AI响应"""
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '''```json
{
  "questions": [
    {
      "question": "What is the correct form?",
      "options": ["A. have gone", "B. went", "C. go", "D. going"],
      "answer": "A",
      "explanation": "Present perfect tense uses 'have/has + past participle'"
    }
  ]
}
```'''
                }
            }
        ]
    }


@pytest.fixture
def mock_wechat_pay_response():
    """Mock微信支付响应"""
    return {
        "return_code": "SUCCESS",
        "result_code": "SUCCESS",
        "prepay_id": "wx_prepay_id_123",
        "trade_type": "JSAPI",
        "code_url": "weixin://wxpay/bizpayurl?pr=xxxxx"
    }


# ==================== 环境变量fixtures ====================
@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock环境变量"""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("JWT_SECRET_KEY", "test_secret_key_at_least_32_chars_long")
    monkeypatch.setenv("ADMIN_PASSWORD", "test_password")
    monkeypatch.setenv("BASE_URL", "http://test.example.com")
    monkeypatch.setenv("ZHIPU_API_KEY", "test_zhipu_key")
    monkeypatch.setenv("FREE_DAILY_LIMIT", "10")
    return monkeypatch


# ==================== Freezegun fixtures ====================
@pytest.fixture
def freeze_time():
    """时间冻结fixture"""
    from freezegun import freeze_time
    return freeze_time("2024-02-08 12:00:00")
