"""
额度管理模块单元测试
"""
import pytest
from datetime import datetime, timedelta
from freezegun import freeze_time

from quota import (
    get_or_create_quota,
    consume_user_quota,
    get_quota_info,
    add_quota,
    activate_subscription
)
from models import Quota


@pytest.mark.unit
@pytest.mark.quota
class TestQuotaCreation:
    """额度创建测试"""

    def test_get_or_create_quota_new_user(self, test_db: Session, test_user: User):
        """测试为新用户创建额度"""
        quota = get_or_create_quota(test_db, test_user.id)

        assert quota is not None
        assert quota.user_id == test_user.id
        assert quota.free_used_today == 0
        assert quota.purchased_count == 0
        assert quota.subscription_expires_at is None

    def test_get_existing_quota(self, test_db: Session, test_user_with_quota: User):
        """测试获取已存在的额度"""
        quota = get_or_create_quota(test_db, test_user_with_quota.id)

        assert quota.purchased_count == 50


@pytest.mark.unit
@pytest.mark.quota
class TestQuotaConsumption:
    """额度消费测试"""

    def test_consume_free_quota_success(self, test_db: Session, test_user: User):
        """测试消费免费额度成功"""
        success, source, result = consume_user_quota(test_db, test_user.id, free_limit=10)

        assert success is True
        assert source == "free"
        assert result == 9  # 剩余9次

    def test_consume_purchased_quota_success(self, test_db: Session, test_user_with_quota: User):
        """测试消费购买额度成功"""
        success, source, result = consume_user_quota(test_db, test_user_with_quota.id)

        assert success is True
        assert source == "purchased"
        assert result == 49  # 剩余49次

    def test_consume_subscription_unlimited(self, test_db: Session, test_subscriber: User):
        """测试订阅用户无限额度"""
        success, source, result = consume_user_quota(test_db, test_subscriber.id)

        assert success is True
        assert source == "subscription"
        assert result == -1  # -1表示无限

    def test_consume_insufficient_quota(self, test_db: Session, test_user: User):
        """测试额度不足"""
        # 先用完所有免费额度
        for _ in range(10):
            consume_user_quota(test_db, test_user.id, free_limit=10)

        # 尝试再次消费
        success, source, result = consume_user_quota(test_db, test_user.id, free_limit=10)

        assert success is False
        assert source == "insufficient"

    def test_quota_priority_subscription_first(self, test_db: Session):
        """测试额度优先级：订阅优先"""
        from datetime import datetime, timedelta

        # 创建有订阅和购买次数的用户
        user = User(
            email="priority_test@example.com",
            password_hash="hash"
        )
        test_db.add(user)
        test_db.commit()

        quota = Quota(
            user_id=user.id,
            purchased_count=100,
            subscription_expires_at=datetime.now() + timedelta(days=30)
        )
        test_db.add(quota)
        test_db.commit()

        success, source, result = consume_user_quota(test_db, user.id)

        # 应该使用订阅额度，而不是购买次数
        assert success is True
        assert source == "subscription"
        assert result == -1

        # 购买次数应该没有减少
        test_db.refresh(quota)
        assert quota.purchased_count == 100


@pytest.mark.unit
@pytest.mark.quota
class TestQuotaInfo:
    """额度信息测试"""

    def test_get_quota_info_free_user(self, test_db: Session, test_user: User):
        """测试获取免费用户额度信息"""
        info = get_quota_info(test_db, test_user)

        assert info["free_limit"] == 10
        assert info["free_used_today"] == 0
        assert info["free_remaining"] == 10
        assert info["purchased_count"] == 0
        assert info["is_subscriber"] is False

    def test_get_quota_info_with_purchased(self, test_db: Session, test_user_with_quota: User):
        """测试获取有购买次数的用户额度信息"""
        info = get_quota_info(test_db, test_user_with_quota)

        assert info["purchased_count"] == 50
        assert info["is_subscriber"] is False

    def test_get_quota_info_subscriber(self, test_db: Session, test_subscriber: User):
        """测试获取订阅用户额度信息"""
        info = get_quota_info(test_db, test_subscriber)

        assert info["is_subscriber"] is True
        assert info["subscription_expires_at"] is not None


@pytest.mark.unit
@pytest.mark.quota
class TestQuotaOperations:
    """额度操作测试"""

    def test_add_quota_package(self, test_db: Session, test_user: User):
        """测试添加次数包"""
        quota = get_or_create_quota(test_db, test_user.id)

        add_quota(test_db, test_user.id, 100)

        test_db.refresh(quota)
        assert quota.purchased_count == 100

    def test_add_quota_existing(self, test_db: Session, test_user_with_quota: User):
        """测试给已有额度的用户添加"""
        quota = get_or_create_quota(test_db, test_user_with_quota.id)
        initial_count = quota.purchased_count

        add_quota(test_db, test_user_with_quota.id, 50)

        test_db.refresh(quota)
        assert quota.purchased_count == initial_count + 50

    def test_activate_subscription_new(self, test_db: Session, test_user: User):
        """测试激活新订阅"""
        quota = get_or_create_quota(test_db, test_user.id)

        activate_subscription(test_db, test_user.id, days=30)

        test_db.refresh(quota)
        assert quota.subscription_expires_at is not None

        # 检查过期时间约为30天后
        time_diff = quota.subscription_expires_at - datetime.now()
        assert time_diff.days >= 29
        assert time_diff.days <= 30

    def test_activate_subscription_extend_existing(self, test_db: Session, test_subscriber: User):
        """测试延长现有订阅"""
        quota = get_or_create_quota(test_db, test_subscriber.id)
        original_expiry = quota.subscription_expires_at

        activate_subscription(test_db, test_subscriber.id, days=30)

        test_db.refresh(quota)
        # 新的过期时间应该比原来的晚30天
        time_diff = quota.subscription_expires_at - original_expiry
        assert time_diff.days >= 29
        assert time_diff.days <= 30


@pytest.mark.unit
@pytest.mark.quota
class TestDailyReset:
    """每日重置测试"""

    @freeze_time("2024-02-08 23:59:59")
    def test_midnight_reset(self, test_db: Session, test_user: User):
        """测试午夜重置"""
        # 先消费一些额度
        consume_user_quota(test_db, test_user.id, free_limit=10)
        consume_user_quota(test_db, test_user.id, free_limit=10)

        quota = get_or_create_quota(test_db, test_user.id)
        assert quota.free_used_today == 2

        # 冻结时间到第二天
        with freeze_time("2024-02-09 00:00:01"):
            # 手动调用重置逻辑（模拟APScheduler）
            from quota import reset_daily_quotas_if_needed
            reset_daily_quotas_if_needed(test_db)

            test_db.refresh(quota)
            assert quota.free_used_today == 0

    def test_reset_only_once_per_day(self, test_db: Session, test_user: User):
        """测试每天只重置一次"""
        from quota import reset_daily_quotas_if_needed

        with freeze_time("2024-02-08 12:00:00"):
            reset_daily_quotas_if_needed(test_db)

        with freeze_time("2024-02-08 12:00:01"):
            # 第二次调用不应该重置
            quota = get_or_create_quota(test_db, test_user.id)
            quota.free_used_today = 5

            reset_daily_quotas_if_needed(test_db)

            test_db.refresh(quota)
            assert quota.free_used_today == 5


@pytest.mark.integration
@pytest.mark.quota
class TestQuotaIntegration:
    """额度集成测试"""

    def test_full_quota_cycle(self, test_db: Session, test_user: User):
        """测试完整的额度周期"""
        # 1. 初始状态
        info = get_quota_info(test_db, test_user)
        assert info["free_remaining"] == 10

        # 2. 消费5次
        for _ in range(5):
            consume_user_quota(test_db, test_user.id)

        # 3. 检查剩余
        info = get_quota_info(test_db, test_user)
        assert info["free_remaining"] == 5

        # 4. 添加购买次数
        add_quota(test_db, test_user.id, 100)

        # 5. 检查总额度
        info = get_quota_info(test_db, test_user)
        assert info["purchased_count"] == 100

        # 6. 消费购买次数
        consume_user_quota(test_db, test_user.id)

        # 7. 检查购买次数减少
        info = get_quota_info(test_db, test_user)
        assert info["purchased_count"] == 99

        # 8. 激活订阅
        activate_subscription(test_db, test_user.id, days=30)

        # 9. 验证订阅状态
        info = get_quota_info(test_db, test_user)
        assert info["is_subscriber"] is True
