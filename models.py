"""
数据模型定义 - PostgreSQL
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlmodel import SQLModel, Field, Session, select
from pydantic import BaseModel


# ==================== SQLModel 模型 ====================
class User(SQLModel, table=True):
    """用户表"""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    password_hash: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=datetime.now)
    last_login_at: Optional[datetime] = None


class Quota(SQLModel, table=True):
    """用户额度表"""
    __tablename__ = "quotas"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True, index=True)
    free_used_today: int = Field(default=0, description="今日已用免费次数")
    free_reset_date: Optional[datetime] = Field(default=None, description="上次重置日期")
    purchased_count: int = Field(default=0, description="已购买次数")
    subscription_expires_at: Optional[datetime] = Field(default=None, description="订阅到期时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class Order(SQLModel, table=True):
    """订单表"""
    __tablename__ = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    order_no: str = Field(unique=True, index=True, max_length=64, description="订单号")
    type: str = Field(max_length=20, description="订单类型：package或subscription")
    amount: int = Field(description="金额（分）")
    status: str = Field(default="pending", max_length=20, description="订单状态：pending/paid/cancelled")
    wechat_prepay_id: Optional[str] = Field(default=None, max_length=255, description="微信支付预支付ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    paid_at: Optional[datetime] = Field(default=None, description="支付时间")


class HomeworkItem(SQLModel, table=True):
    """作业数据表"""
    __tablename__ = "homework_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")  # 关联用户
    short_id: str = Field(unique=True, index=True, max_length=12)  # 8位短码
    content: str = Field(max_length=10000)  # 作业内容（Markdown）
    title: Optional[str] = Field(default=None, max_length=100)  # 自动提取的首行
    audio_path: Optional[str] = Field(default=None, max_length=255)  # 音频文件路径
    audio_filename: Optional[str] = Field(default=None, max_length=100)  # 原始文件名
    audio_size: Optional[int] = Field(default=None)  # 文件大小（字节）
    homework_type: str = Field(default="text", max_length=20)  # 'text' 或 'listening'
    grade: Optional[str] = Field(default=None, max_length=50)  # 年级（AI生成）
    topic: Optional[str] = Field(default=None, max_length=100)  # 主题（AI生成）
    difficulty: Optional[str] = Field(default=None, max_length=20)  # 难度（AI生成）
    question_types: Optional[str] = Field(default=None, max_length=100)  # JSON格式的题型列表
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = Field(default=None)  # 扩展字段，预留


# ==================== Pydantic Models for API ====================
class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    email: str
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class QuotaResponse(BaseModel):
    """额度响应模型"""
    free_used_today: int
    free_limit: int
    purchased_count: int
    is_subscriber: bool
    subscription_expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class QuotaConsumeResponse(BaseModel):
    """额度消费响应模型"""
    remaining: int
    type: str  # 'free', 'purchased', 'subscription'


class OrderCreate(BaseModel):
    """创建订单请求"""
    type: str  # 'package' 或 'subscription'
    amount: int  # 金额（分）


class OrderResponse(BaseModel):
    """订单响应模型"""
    id: int
    order_no: str
    type: str
    amount: int
    status: str
    created_at: datetime
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HomeworkCreate(BaseModel):
    """创建作业的请求模型"""
    content: str
    homework_type: str = "text"  # 'static', 'text', 'listening'


class HomeworkResponse(BaseModel):
    """作业响应模型"""
    short_id: str
    title: Optional[str]
    content: str
    audio_filename: Optional[str]
    audio_size: Optional[int]
    homework_type: str
    created_at: datetime


class QRCodeRequest(BaseModel):
    """生成二维码请求"""
    content: str
    mode: str  # 'static' or 'dynamic'
    access_code: str
    size: int = 300
    error_correction: str = "M"


class QRCodeResponse(BaseModel):
    """二维码响应"""
    qr_code_data_url: str  # Base64 编码的 PNG 图片
    short_id: Optional[str] = None  # 活码模式返回短 ID
    mode: str


class AudioUploadResponse(BaseModel):
    """音频上传响应"""
    filename: str
    path: str
    size: int
    url: str


# ==================== Database Operations ====================
# 导入数据库连接（从database.py）
from database import engine


def init_db():
    """初始化数据库"""
    SQLModel.metadata.create_all(engine)
    print("✅ Database initialized (PostgreSQL)")


def get_session():
    """获取数据库会话"""
    with Session(engine) as session:
        yield session


# ==================== 用户操作 ====================
def get_user_by_email(session: Session, email: str) -> Optional[User]:
    """根据邮箱获取用户"""
    statement = select(User).where(User.email == email)
    result = session.exec(statement).first()
    return result


def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
    """根据ID获取用户"""
    return session.get(User, user_id)


def create_user(session: Session, email: str, password_hash: str) -> User:
    """创建新用户"""
    user = User(email=email, password_hash=password_hash)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def update_last_login(session: Session, user: User):
    """更新用户最后登录时间"""
    user.last_login_at = datetime.now()
    session.add(user)
    session.commit()


# ==================== 额度操作 ====================
def get_user_quota(session: Session, user_id: int) -> Optional[Quota]:
    """获取用户额度"""
    return session.query(Quota).filter(Quota.user_id == user_id).first()


def create_user_quota(session: Session, user_id: int, free_limit: int = 10) -> Quota:
    """创建用户额度（新用户注册时调用）"""
    quota = Quota(
        user_id=user_id,
        free_used_today=0,
        free_reset_date=datetime.now().date(),
        purchased_count=0
    )
    session.add(quota)
    session.commit()
    session.refresh(quota)
    return quota


def check_daily_reset_needed(session: Session, quota: Quota) -> bool:
    """检查是否需要每日重置"""
    if quota.free_reset_date is None:
        return True

    today = datetime.now().date()
    reset_date = quota.free_reset_date

    if isinstance(reset_date, datetime):
        reset_date = reset_date.date()

    return today > reset_date


def reset_daily_quota(session: Session, quota: Quota):
    """重置每日免费额度"""
    quota.free_used_today = 0
    quota.free_reset_date = datetime.now().date()
    session.add(quota)
    session.commit()


def consume_quota(session: Session, user_id: int, free_limit: int = 10) -> tuple[bool, str, int]:
    """
    消费额度

    Returns:
        tuple[bool, str, int]: (是否成功, 消费类型, 剩余额度)
        消费类型：'free', 'purchased', 'subscription'
    """
    quota = get_user_quota(session, user_id)

    if not quota:
        quota = create_user_quota(session, user_id, free_limit)

    # 检查是否需要每日重置
    if check_daily_reset_needed(session, quota):
        reset_daily_quota(session, quota)

    # 1. 检查是否是订阅用户
    if quota.subscription_expires_at:
        if quota.subscription_expires_at > datetime.now():
            return True, 'subscription', -1  # -1 表示无限

    # 2. 使用购买次数
    if quota.purchased_count > 0:
        quota.purchased_count -= 1
        session.add(quota)
        session.commit()
        return True, 'purchased', quota.purchased_count

    # 3. 使用免费次数
    if quota.free_used_today < free_limit:
        quota.free_used_today += 1
        session.add(quota)
        session.commit()
        return True, 'free', free_limit - quota.free_used_today

    # 4. 额度不足
    return False, 'insufficient', 0


def add_purchased_count(session: Session, user_id: int, count: int):
    """增加购买次数"""
    quota = get_user_quota(session, user_id)
    if not quota:
        quota = create_user_quota(session, user_id)

    quota.purchased_count += count
    session.add(quota)
    session.commit()


def set_subscription(session: Session, user_id: int, days: int = 30):
    """设置订阅（从今天开始，days天后到期）"""
    quota = get_user_quota(session, user_id)
    if not quota:
        quota = create_user_quota(session, user_id)

    # 如果已有订阅且未过期，在原基础上延长
    if quota.subscription_expires_at and quota.subscription_expires_at > datetime.now():
        quota.subscription_expires_at = quota.subscription_expires_at + timedelta(days=days)
    else:
        quota.subscription_expires_at = datetime.now() + timedelta(days=days)

    session.add(quota)
    session.commit()


# ==================== 订单操作 ====================
def create_order(session: Session, user_id: int, order_type: str, amount: int) -> Order:
    """创建订单"""
    import uuid
    order_no = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:6].upper()}"

    order = Order(
        user_id=user_id,
        order_no=order_no,
        type=order_type,
        amount=amount,
        status='pending'
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


def get_order_by_no(session: Session, order_no: str) -> Optional[Order]:
    """根据订单号获取订单"""
    return session.query(Order).filter(Order.order_no == order_no).first()


def update_order_paid(session: Session, order: Order, wechat_prepay_id: str = None):
    """更新订单为已支付"""
    order.status = 'paid'
    order.paid_at = datetime.now()
    if wechat_prepay_id:
        order.wechat_prepay_id = wechat_prepay_id
    session.add(order)
    session.commit()


def get_user_orders(session: Session, user_id: int, limit: int = 20, offset: int = 0):
    """获取用户订单列表"""
    return session.query(Order).filter(Order.user_id == user_id).order_by(Order.created_at.desc()).limit(limit).offset(offset).all()


# ==================== 作业操作 ====================

def save_homework(
    session: Session,
    short_id: str,
    content: str,
    title: Optional[str] = None,
    audio_path: Optional[str] = None,
    audio_filename: Optional[str] = None,
    audio_size: Optional[int] = None,
    homework_type: str = "text"
) -> HomeworkItem:
    """保存作业到数据库"""
    homework = HomeworkItem(
        short_id=short_id,
        content=content,
        title=title,
        audio_path=audio_path,
        audio_filename=audio_filename,
        audio_size=audio_size,
        homework_type=homework_type
    )
    session.add(homework)
    session.commit()
    session.refresh(homework)
    return homework


def get_homework_by_short_id(session: Session, short_id: str) -> Optional[HomeworkItem]:
    """根据短 ID 获取作业"""
    statement = select(HomeworkItem).where(HomeworkItem.short_id == short_id)
    result = session.exec(statement).first()
    return result


def delete_homework(session: Session, homework: HomeworkItem):
    """删除作业记录"""
    session.delete(homework)
    session.commit()


def delete_expired_homeworks(session: Session, days: int = 30):
    """删除过期的作业记录"""
    from datetime import timedelta
    expiration_date = datetime.now() - timedelta(days=days)
    statement = select(HomeworkItem).where(HomeworkItem.created_at < expiration_date)
    expired_items = session.exec(statement).all()

    deleted_count = 0
    for item in expired_items:
        # 删除关联的音频文件
        if item.audio_path:
            try:
                import os
                full_path = os.path.join("/app/static/uploads", item.audio_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
                    print(f"🗑️  Deleted audio file: {full_path}")
            except Exception as e:
                print(f"⚠️  Failed to delete audio file: {e}")

        session.delete(item)
        deleted_count += 1

    session.commit()
    return deleted_count
