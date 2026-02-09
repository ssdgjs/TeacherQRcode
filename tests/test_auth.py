"""
认证模块单元测试
"""
import pytest
from sqlmodel import Session, select

from auth import (
    get_password_hash,
    verify_password,
    validate_password_strength,
    validate_email,
    create_access_token
)
from models import User


class TestPasswordHashing:
    """密码哈希测试"""

    def test_get_password_hash(self):
        """测试密码哈希生成"""
        password = "password123"
        hash_result = get_password_hash(password)

        assert hash_result != password
        assert len(hash_result) > 50
        assert hash_result.startswith("$2b$")

    def test_verify_password_correct(self):
        """测试正确密码验证"""
        password = "password123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """测试错误密码验证"""
        password = "password123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False


class TestPasswordValidation:
    """密码验证测试"""

    def test_valid_password(self):
        """测试有效密码"""
        password = "Test1234"
        is_valid, msg = validate_password_strength(password)

        assert is_valid is True
        assert msg == ""

    def test_password_too_short(self):
        """测试密码太短"""
        password = "Test1"
        is_valid, msg = validate_password_strength(password)

        assert is_valid is False
        assert "至少8个字符" in msg

    def test_password_no_letter(self):
        """测试密码没有字母"""
        password = "12345678"
        is_valid, msg = validate_password_strength(password)

        assert is_valid is False
        assert "必须包含字母" in msg

    def test_password_no_digit(self):
        """测试密码没有数字"""
        password = "abcdefgh"
        is_valid, msg = validate_password_strength(password)

        assert is_valid is False
        assert "必须包含数字" in msg


class TestEmailValidation:
    """邮箱验证测试"""

    def test_valid_email(self):
        """测试有效邮箱"""
        email = "test@example.com"
        is_valid, msg = validate_email(email)

        assert is_valid is True
        assert msg == ""

    def test_invalid_email_no_at(self):
        """测试无效邮箱（没有@）"""
        email = "testexample.com"
        is_valid, msg = validate_email(email)

        assert is_valid is False
        assert "无效的邮箱地址" in msg

    def test_invalid_email_no_domain(self):
        """测试无效邮箱（没有域名）"""
        email = "test@"
        is_valid, msg = validate_email(email)

        assert is_valid is False

    def test_invalid_email_format(self):
        """测试无效邮箱格式"""
        email = "@example.com"
        is_valid, msg = validate_email(email)

        assert is_valid is False


class TestJWTToken:
    """JWT Token测试"""

    def test_create_access_token(self):
        """测试创建访问token"""
        data = {"sub": 1, "email": "test@example.com"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50

    def test_token_contains_user_data(self):
        """测试token包含用户数据"""
        from auth import jwt

        data = {"sub": 1, "email": "test@example.com"}
        token = create_access_token(data)

        # 解码token
        from auth import ALGORITHM, SECRET_KEY
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert decoded["sub"] == 1
        assert decoded["email"] == "test@example.com"
        assert "exp" in decoded

    def test_token_expiration(self):
        """测试token过期时间"""
        from auth import jwt
        from datetime import datetime, timedelta

        data = {"sub": 1, "email": "test@example.com"}
        token = create_access_token(data)

        from auth import ALGORITHM, SECRET_KEY
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # 检查过期时间约为7天后
        exp_time = datetime.fromtimestamp(decoded["exp"])
        now = datetime.utcnow()
        time_diff = exp_time - now

        assert time_diff.days >= 6
        assert time_diff.days <= 7


@pytest.mark.unit
@pytest.mark.auth
class TestAuthIntegration:
    """认证集成测试（使用测试数据库）"""

    def test_create_user_in_db(self, test_db: Session):
        """测试在数据库中创建用户"""
        user = User(
            email="newuser@example.com",
            password_hash=get_password_hash("password123")
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.password_hash.startswith("$2b$")

    def test_find_user_by_email(self, test_db: Session, test_user: User):
        """测试通过邮箱查找用户"""
        found_user = test_db.exec(
            select(User).where(User.email == test_user.email)
        ).first()

        assert found_user is not None
        assert found_user.id == test_user.id

    def test_duplicate_email_rejected(self, test_db: Session, test_user: User):
        """测试重复邮箱被拒绝"""
        # 尝试创建相同邮箱的用户
        duplicate_user = User(
            email=test_user.email,
            password_hash=get_password_hash("different_password")
        )

        test_db.add(duplicate_user)

        with pytest.raises(Exception):  # 应该抛出IntegrityError
            test_db.commit()
