"""
额度管理系统
"""
from typing import Optional
from sqlmodel import Session
from models import Quota, User, get_user_quota, create_user_quota, consume_quota
from pydantic_settings import BaseSettings


class QuotaSettings(BaseSettings):
    """额度配置"""
    free_daily_limit: int = 10  # 每日免费次数上限
    package_price_100: int = 990  # 100次价格（分）
    monthly_price: int = 990  # 月卡价格（分）

    class Config:
        env_file = ".env"
        extra = "ignore"  # 忽略额外的环境变量
        env_prefix = ""


quota_settings = QuotaSettings()


def get_or_create_quota(session: Session, user_id: int) -> Quota:
    """
    获取或创建用户额度

    Args:
        session: 数据库会话
        user_id: 用户ID

    Returns:
        Quota: 用户额度对象
    """
    quota = get_user_quota(session, user_id)
    if not quota:
        quota = create_user_quota(session, user_id, quota_settings.free_daily_limit)
    return quota


def get_quota_info(session: Session, user: User) -> dict:
    """
    获取用户额度信息（用于API响应）

    Args:
        session: 数据库会话
        user: 用户对象

    Returns:
        dict: 额度信息
    """
    from datetime import datetime

    quota = get_or_create_quota(session, user.id)

    # 检查订阅状态
    is_subscriber = False
    subscription_expires_at = None

    if quota.subscription_expires_at:
        is_subscriber = quota.subscription_expires_at > datetime.now()
        if is_subscriber:
            subscription_expires_at = quota.subscription_expires_at.isoformat()

    return {
        "free_used_today": quota.free_used_today,
        "free_limit": quota_settings.free_daily_limit,
        "purchased_count": quota.purchased_count,
        "is_subscriber": is_subscriber,
        "subscription_expires_at": subscription_expires_at
    }


def can_consume_quota(session: Session, user_id: int) -> tuple[bool, str]:
    """
    检查是否可以消费额度

    Args:
        session: 数据库会话
        user_id: 用户ID

    Returns:
        tuple[bool, str]: (是否可以消费, 错误信息)
    """
    from datetime import datetime

    quota = get_or_create_quota(session, user_id)

    # 1. 检查订阅
    if quota.subscription_expires_at and quota.subscription_expires_at > datetime.now():
        return True, ""

    # 2. 检查购买次数
    if quota.purchased_count > 0:
        return True, ""

    # 3. 检查免费次数
    if quota.free_used_today < quota_settings.free_daily_limit:
        return True, ""

    # 4. 额度不足
    return False, "今日免费次数已用完，请购买次数包或订阅月卡"


def consume_user_quota(session: Session, user_id: int) -> tuple[bool, str, dict]:
    """
    消费用户额度

    Args:
        session: 数据库会话
        user_id: 用户ID

    Returns:
        tuple[bool, str, dict]: (是否成功, 消息, 额度信息)
    """
    from datetime import datetime

    # 先检查是否可以消费
    can_consume, error_msg = can_consume_quota(session, user_id)
    if not can_consume:
        return False, error_msg, {}

    # 消费额度
    success, consume_type, remaining = consume_quota(session, user_id, quota_settings.free_daily_limit)

    if not success:
        return False, "消费额度失败", {}

    # 获取更新后的额度信息
    quota = get_or_create_quota(session, user_id)

    result = {
        "consume_type": consume_type,
        "remaining": remaining if consume_type != 'subscription' else -1,
        "free_used_today": quota.free_used_today,
        "free_limit": quota_settings.free_daily_limit,
        "purchased_count": quota.purchased_count,
        "is_subscriber": quota.subscription_expires_at and quota.subscription_expires_at > datetime.now()
    }

    return True, "消费成功", result


def reset_all_daily_quotas(session: Session) -> int:
    """
    重置所有用户的每日免费额度（定时任务调用）

    Args:
        session: 数据库会话

    Returns:
        int: 重置的用户数量
    """
    from datetime import datetime, date

    today = date.today()

    # 查找需要重置的用户
    quotas = session.query(Quota).filter(
        (Quota.free_reset_date != today) | (Quota.free_reset_date.is_(None))
    ).all()

    count = 0
    for quota in quotas:
        quota.free_used_today = 0
        quota.free_reset_date = today
        session.add(quota)
        count += 1

    session.commit()
    return count


def add_quota(session: Session, user_id: int, count: int) -> bool:
    """
    增加购买次数（支付成功后调用）

    Args:
        session: 数据库会话
        user_id: 用户ID
        count: 增加的次数

    Returns:
        bool: 是否成功
    """
    try:
        from models import add_purchased_count
        add_purchased_count(session, user_id, count)
        return True
    except Exception as e:
        print(f"增加次数失败: {e}")
        return False


def activate_subscription(session: Session, user_id: int, days: int = 30) -> bool:
    """
    激活订阅（支付成功后调用）

    Args:
        session: 数据库会话
        user_id: 用户ID
        days: 订阅天数

    Returns:
        bool: 是否成功
    """
    try:
        from models import set_subscription
        set_subscription(session, user_id, days)
        return True
    except Exception as e:
        print(f"激活订阅失败: {e}")
        return False
