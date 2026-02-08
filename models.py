"""
数据模型定义 - SQLite
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, create_engine, Session, select
from pydantic import BaseModel
import os


# ==================== SQLModel ====================
class HomeworkItem(SQLModel, table=True):
    """作业数据表"""
    __tablename__ = "homework_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    short_id: str = Field(unique=True, index=True, max_length=12)  # 8位短码
    content: str = Field(max_length=10000)  # 作业内容（Markdown）
    title: Optional[str] = Field(default=None, max_length=100)  # 自动提取的首行
    audio_path: Optional[str] = Field(default=None, max_length=255)  # 音频文件路径
    audio_filename: Optional[str] = Field(default=None, max_length=100)  # 原始文件名
    audio_size: Optional[int] = Field(default=None)  # 文件大小（字节）
    homework_type: str = Field(default="text", max_length=20)  # 'text' 或 'listening'
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = Field(default=None)  # 扩展字段，预留


# ==================== Pydantic Models for API ====================
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


# ==================== Database Engine ====================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/data.db")
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def init_db():
    """初始化数据库"""
    SQLModel.metadata.create_all(engine)
    print("✅ Database initialized at:", DATABASE_URL)


def get_session():
    """获取数据库会话"""
    with Session(engine) as session:
        yield session


# ==================== Database Operations ====================
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
