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
    # 新增字段：关联的抽卡历史（通过反向关联）


class GenerationHistory(SQLModel, table=True):
    """抽卡历史记录表"""
    __tablename__ = "generation_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    homework_id: int = Field(foreign_key="homework_items.id", index=True, description="关联的作业ID")
    user_id: int = Field(foreign_key="users.id", index=True, description="用户ID")
    version: int = Field(default=1, description="版本号（从1开始）")
    content: str = Field(description="完整的生成内容（JSON格式）")
    prompt: Optional[str] = Field(default=None, max_length=2000, description="使用的提示词")
    previous_context: Optional[str] = Field(default=None, description="之前的历史上下文（最多5次）")
    voice_config: Optional[str] = Field(default=None, max_length=500, description="音色配置（JSON格式，仅听力题）")
    is_active: bool = Field(default=True, index=True, description="是否是当前使用的版本")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    extra_data: Optional[str] = Field(default=None, description="额外元数据（AI参数等）")


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
    homework_type: str = "text",
    user_id: Optional[int] = None
) -> HomeworkItem:
    """保存作业到数据库"""
    homework = HomeworkItem(
        user_id=user_id,  # 添加 user_id
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


# ==================== 抽卡历史操作 ====================

def create_generation_history(
    session: Session,
    homework_id: int,
    user_id: int,
    content: str,
    prompt: Optional[str] = None,
    previous_context: Optional[str] = None,
    voice_config: Optional[str] = None,
    metadata: Optional[str] = None
) -> GenerationHistory:
    """
    创建新的抽卡历史记录

    自动处理版本号和旧版本标记
    """
    # 获取当前最大版本号
    statement = select(GenerationHistory).where(
        GenerationHistory.homework_id == homework_id
    ).order_by(GenerationHistory.version.desc())
    latest = session.exec(statement).first()

    next_version = (latest.version + 1) if latest else 1

    # 如果不是第一个版本，将旧版本标记为非活跃
    if latest and latest.is_active:
        latest.is_active = False
        session.add(latest)

    # 创建新历史记录
    history = GenerationHistory(
        homework_id=homework_id,
        user_id=user_id,
        version=next_version,
        content=content,
        prompt=prompt,
        previous_context=previous_context,
        voice_config=voice_config,
        is_active=True,
        metadata=metadata
    )
    session.add(history)
    session.commit()
    session.refresh(history)
    return history


def get_generation_history(session: Session, homework_id: int) -> list[GenerationHistory]:
    """获取某个作业的所有抽卡历史"""
    statement = select(GenerationHistory).where(
        GenerationHistory.homework_id == homework_id
    ).order_by(GenerationHistory.version.desc())
    return session.exec(statement).all()


def get_active_generation(session: Session, homework_id: int) -> Optional[GenerationHistory]:
    """获取某个作业当前使用的版本"""
    statement = select(GenerationHistory).where(
        GenerationHistory.homework_id == homework_id,
        GenerationHistory.is_active == True
    )
    return session.exec(statement).first()


def set_active_generation(session: Session, history_id: int) -> Optional[GenerationHistory]:
    """
    设置某个版本为当前使用版本

    会将同一作业的其他版本标记为非活跃
    """
    history = session.get(GenerationHistory, history_id)
    if not history:
        return None

    homework_id = history.homework_id

    # 将同作业的其他版本标记为非活跃
    statement = select(GenerationHistory).where(
        GenerationHistory.homework_id == homework_id,
        GenerationHistory.is_active == True,
        GenerationHistory.id != history_id
    )
    others = session.exec(statement).all()
    for other in others:
        other.is_active = False
        session.add(other)

    # 设置当前版本为活跃
    history.is_active = True
    session.add(history)
    session.commit()
    session.refresh(history)
    return history


def build_context_from_history(session: Session, homework_id: int, max_history: int = 5) -> str:
    """
    从历史记录构建上下文（用于AI抽卡）

    Args:
        homework_id: 作业ID
        max_history: 最多保留的历史次数（默认5次）

    Returns:
        str: 格式化的历史上下文字符串
    """
    statement = select(GenerationHistory).where(
        GenerationHistory.homework_id == homework_id
    ).order_by(GenerationHistory.version.desc()).limit(max_history)
    histories = session.exec(statement).all()

    if not histories:
        return ""

    # 按时间顺序（从旧到新）构建上下文
    contexts = []
    for h in reversed(histories):
        context_parts = [f"## 版本 {h.version}"]
        if h.prompt:
            context_parts.append(f"提示词: {h.prompt}")
        if h.voice_config:
            context_parts.append(f"音色配置: {h.voice_config}")
        contexts.append("\n".join(context_parts))

    return "\n\n---\n\n".join(contexts)
