"""
EduQR Lite - 简易作业二维码生成器
FastAPI 主应用
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Response, UploadFile, File, Form, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from sqlalchemy import select

from models import (
    init_db, get_session, HomeworkItem, HomeworkCreate,
    HomeworkResponse, delete_expired_homeworks, get_homework_by_short_id,
    save_homework, delete_homework, update_homework, User, UserResponse,
    get_user_by_email, create_user, update_last_login,
    get_user_by_id, QuotaResponse, QuotaConsumeResponse
)
from auth import (
    UserLogin, UserRegister, Token, get_current_user,
    create_access_token, verify_password, get_password_hash,
    validate_password_strength, validate_email
)
from quota import (
    get_quota_info, can_consume_quota, consume_user_quota,
    add_quota, activate_subscription
)
from tasks import start_scheduler, get_scheduler_info
from ai_service import get_ai_service, validate_generation_params
from tts_service import get_tts_service, validate_tts_params, VOICE_CONFIGS, SPEED_CONFIGS
from utils import (
    generate_short_id, generate_qr_code, extract_title,
    render_markdown, sanitize_markdown, format_file_size,
    format_timestamp, validate_content_length, validate_audio_file,
    get_recommended_mode
)
from pydantic_settings import BaseSettings


# ==================== Configuration ====================
class Settings(BaseSettings):
    """应用配置"""
    admin_password: str = "changeme"
    base_url: str = "http://localhost:8000"
    data_retention_days: int = 30
    max_content_length: int = 10000
    max_upload_size_mb: int = 20
    allowed_audio_extensions: str = "mp3,wav,m4a,ogg"  # 改为字符串
    qr_code_size: int = 300
    qr_error_correction: str = "M"

    class Config:
        env_file = ".env"

    @property
    def allowed_extensions_list(self) -> list:
        """将字符串转换为列表"""
        return [ext.strip() for ext in self.allowed_audio_extensions.split(',')]


settings = Settings()


# ==================== FastAPI App ====================
app = FastAPI(
    title="EduQR Lite",
    description="简易作业二维码生成器",
    version="1.1.0"
)

# 初始化数据库
init_db()

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 创建必要的目录（支持本地和 Docker 环境）
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "static" / "uploads")))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "static" / "output")))
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 挂载静态文件
static_dir = Path(os.getenv("STATIC_DIR", str(BASE_DIR / "static")))
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 模板引擎
templates_dir = Path(os.getenv("TEMPLATES_DIR", str(BASE_DIR / "templates")))
templates = Jinja2Templates(directory=str(templates_dir))


# ==================== Startup Event ====================
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print("=" * 50)
    print("🚀 EduQR AI 启动成功！")
    print(f"📡 Base URL: {settings.base_url}")
    print(f"🔒 Admin Password: {'已设置' if settings.admin_password != 'changeme' else '警告：使用默认密码'}")
    print(f"📁 Upload Directory: {UPLOAD_DIR}")
    print(f"📅 Data Retention: {settings.data_retention_days} 天")
    print("=" * 50)

    # 清理过期数据
    try:
        with next(get_session()) as session:
            deleted_count = delete_expired_homeworks(session, days=settings.data_retention_days)
            if deleted_count > 0:
                print(f"🗑️  已清理 {deleted_count} 条过期作业记录")
    except Exception as e:
        print(f"⚠️  清理过期数据时出错: {e}")

    # 启动定时任务调度器
    try:
        start_scheduler()
        print("🕐 定时任务调度器已启动")
    except Exception as e:
        print(f"⚠️  启动定时任务调度器失败: {e}")


# ==================== Health Check ====================
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ==================== SEO Routes ====================
@app.get("/robots.txt")
async def robots_txt():
    """Robots.txt"""
    robots_path = Path(os.getenv("STATIC_DIR", str(BASE_DIR / "static"))) / "robots.txt"
    if robots_path.exists():
        return FileResponse(robots_path)
    return FileResponse(BASE_DIR / "static" / "robots.txt")


@app.get("/sitemap.xml")
async def sitemap_xml():
    """Sitemap.xml"""
    sitemap_path = Path(os.getenv("STATIC_DIR", str(BASE_DIR / "static"))) / "sitemap.xml"
    if sitemap_path.exists():
        return FileResponse(sitemap_path)
    return FileResponse(BASE_DIR / "static" / "sitemap.xml")


# ==================== Authentication Routes ====================
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    return templates.TemplateResponse(
        "login.html",
        {"request": request}
    )


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """注册页面"""
    return templates.TemplateResponse(
        "register.html",
        {"request": request}
    )


@app.post("/api/v1/auth/register")
async def register(user_data: UserRegister):
    """
    用户注册

    Args:
        user_data: 注册数据（邮箱、密码、确认密码）

    Returns:
        JSON: success=True 时包含 token 和 user 信息
    """
    # 验证邮箱格式
    is_valid, error_msg = validate_email(user_data.email)
    if not is_valid:
        return {"success": False, "error": error_msg}

    # 验证密码匹配
    if user_data.password != user_data.confirm_password:
        return {"success": False, "error": "两次输入的密码不一致"}

    # 验证密码强度
    is_valid, error_msg = validate_password_strength(user_data.password)
    if not is_valid:
        return {"success": False, "error": error_msg}

    session = next(get_session())

    # 检查邮箱是否已存在
    existing_user = get_user_by_email(session, user_data.email)
    if existing_user:
        return {"success": False, "error": "该邮箱已被注册"}

    try:
        # 创建新用户
        password_hash = get_password_hash(user_data.password)
        new_user = create_user(session, user_data.email, password_hash)

        # 自动创建额度记录
        from quota import get_or_create_quota
        from models import create_user_quota
        quota = create_user_quota(session, new_user.id)

        # 生成 JWT token
        token_data = {
            "sub": new_user.id,
            "email": new_user.email
        }
        access_token = create_access_token(token_data)

        return {
            "success": True,
            "data": {
                "token": access_token,
                "user": {
                    "id": new_user.id,
                    "email": new_user.email,
                    "created_at": new_user.created_at.isoformat()
                }
            }
        }
    except Exception as e:
        return {"success": False, "error": f"注册失败: {str(e)}"}


@app.post("/api/v1/auth/login")
async def login(user_data: UserLogin):
    """
    用户登录

    Args:
        user_data: 登录数据（邮箱、密码）

    Returns:
        JSON: success=True 时包含 token 和 user 信息
    """
    session = next(get_session())

    # 查找用户
    user = get_user_by_email(session, user_data.email)
    if not user:
        return {"success": False, "error": "邮箱或密码错误"}

    # 验证密码
    if not verify_password(user_data.password, user.password_hash):
        return {"success": False, "error": "邮箱或密码错误"}

    try:
        # 更新最后登录时间
        update_last_login(session, user)

        # 生成 JWT token
        token_data = {
            "sub": user.id,
            "email": user.email
        }
        access_token = create_access_token(token_data)

        return {
            "success": True,
            "data": {
                "token": access_token,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "created_at": user.created_at.isoformat(),
                    "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
                }
            }
        }
    except Exception as e:
        return {"success": False, "error": f"登录失败: {str(e)}"}


@app.get("/api/v1/auth/me")
async def get_current_user_info(current_user = Depends(get_current_user)):
    """
    获取当前登录用户信息

    Args:
        current_user: 当前用户（从JWT token解析）

    Returns:
        JSON: 用户信息
    """
    session = next(get_session())
    user = session.get(User, current_user.user_id)

    if not user:
        return {"success": False, "error": "用户不存在"}

    return {
        "success": True,
        "data": {
            "id": user.id,
            "email": user.email,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
        }
    }


# ==================== Quota Management Routes ====================
@app.get("/api/v1/quota")
async def get_user_quota_info(current_user = Depends(get_current_user)):
    """
    获取当前用户额度信息

    Args:
        current_user: 当前用户（从JWT token解析）

    Returns:
        JSON: 额度信息（免费次数、购买次数、订阅状态）
    """
    session = next(get_session())
    user = get_user_by_id(session, current_user.user_id)

    if not user:
        return {"success": False, "error": "用户不存在"}

    try:
        quota_info = get_quota_info(session, user)
        return {"success": True, "data": quota_info}
    except Exception as e:
        return {"success": False, "error": f"获取额度信息失败: {str(e)}"}


@app.post("/api/v1/quota/consume")
async def consume_user_quota_endpoint(current_user = Depends(get_current_user)):
    """
    消费用户额度（AI生成时调用）

    Args:
        current_user: 当前用户（从JWT token解析）

    Returns:
        JSON: 消费结果（剩余额度、消费类型）
    """
    session = next(get_session())

    try:
        success, message, result = consume_user_quota(session, current_user.user_id)

        if not success:
            raise HTTPException(status_code=403, detail=message)

        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": f"消费额度失败: {str(e)}"}


@app.get("/api/v1/scheduler/info")
async def get_scheduler_status():
    """
    获取定时任务状态（管理员用）

    Returns:
        JSON: 调度器状态和任务列表
    """
    try:
        info = get_scheduler_info()
        return {"success": True, "data": info}
    except Exception as e:
        return {"success": False, "error": f"获取调度器信息失败: {str(e)}"}


# ==================== AI Generation Routes ====================
@app.get("/generate", response_class=HTMLResponse)
async def generate_page(request: Request):
    """AI作业生成页面"""
    return templates.TemplateResponse(
        "generate.html",
        {"request": request}
    )


class HomeworkGenerateRequest(BaseModel):
    """AI生成作业请求"""
    grade: str  # 年级
    topic: str  # 主题
    difficulty: str  # 难度：easy/medium/hard
    question_types: list  # 题型列表：[{"type": "choice", "count": 5}]


@app.post("/api/v1/homework/generate")
async def generate_homework(
    request_data: HomeworkGenerateRequest,
    current_user = Depends(get_current_user)
):
    """
    AI生成英语作业

    Args:
        request_data: 生成参数（年级、主题、难度、题型）
        current_user: 当前用户（从JWT token解析）

    Returns:
        JSON: 生成的作业数据
    """
    session = next(get_session())

    # 1. 验证参数
    is_valid, error_msg = validate_generation_params(
        request_data.grade,
        request_data.topic,
        request_data.difficulty,
        request_data.question_types
    )
    if not is_valid:
        return {"success": False, "error": error_msg}

    # 2. 检查并消费额度
    try:
        success, message, result = consume_user_quota(session, current_user.user_id)
        if not success:
            raise HTTPException(status_code=403, detail=message)
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": f"额度检查失败: {str(e)}"}

    # 3. 调用AI生成
    try:
        ai_service = get_ai_service()
        homework_data = ai_service.generate_questions(
            grade=request_data.grade,
            topic=request_data.topic,
            difficulty=request_data.difficulty,
            question_types=request_data.question_types
        )

        # 4. 保存到数据库
        import json
        from datetime import datetime
        import os

        # 生成短ID
        short_id = generate_short_id(8)

        # 准备内容（JSON格式的结构化数据）
        content_json = {
            "id": f"hw_{short_id}",
            "grade": homework_data["grade"],
            "topic": homework_data["topic"],
            "difficulty": homework_data["difficulty"],
            "questions": homework_data["questions"],
            "generated_at": datetime.now().isoformat()
        }
        content = json.dumps(content_json, ensure_ascii=False, indent=2)

        # 提取标题
        title = f"{homework_data['grade']} - {homework_data['topic']}"

        # 保存到数据库
        homework = save_homework(
            session=session,
            short_id=short_id,
            content=content,
            title=title,
            user_id=current_user.user_id,
            homework_type="ai_generated"
        )

        # 5. 生成短链接和二维码
        view_url = f"{settings.base_url}/v/{short_id}"
        qr_data_url = generate_qr_code(view_url, 300, "M")

        return {
            "success": True,
            "data": {
                "homework": homework_data,
                "homework_id": homework.id,
                "short_id": short_id,
                "view_url": view_url,
                "qr_code_data_url": qr_data_url,
                "quota_remaining": result.get("remaining", -1)
            }
        }

    except Exception as e:
        # AI生成失败，退还额度（简化处理，实际应该用事务）
        return {"success": False, "error": f"AI生成失败: {str(e)}"}


@app.get("/api/v1/ai/test")
async def test_ai_connection():
    """
    测试AI服务连接

    Returns:
        JSON: 测试结果
    """
    try:
        ai_service = get_ai_service()
        is_connected = ai_service.test_connection()
        return {
            "success": True,
            "data": {
                "connected": is_connected,
                "model": "glm-4-flash"
            }
        }
    except Exception as e:
        return {"success": False, "error": f"AI服务连接失败: {str(e)}"}


# ==================== TTS Routes ====================
class TTSGenerateRequest(BaseModel):
    """TTS生成请求"""
    text: str
    voice: str = "en_us_male"
    speed: float = 1.0


@app.post("/api/v1/tts/generate")
async def generate_tts_audio(
    request_data: TTSGenerateRequest,
    current_user = Depends(get_current_user)
):
    """
    生成TTS音频

    Args:
        request_data: TTS参数（文本、发音、语速）
        current_user: 当前用户（从JWT token解析）

    Returns:
        JSON: 生成的音频信息
    """
    # 1. 验证参数
    is_valid, error_msg = validate_tts_params(
        request_data.text,
        request_data.voice,
        request_data.speed
    )
    if not is_valid:
        return {"success": False, "error": error_msg}

    # 2. 调用TTS服务
    try:
        tts_service = get_tts_service()
        audio_data = tts_service.generate_audio(
            text=request_data.text,
            voice=request_data.voice,
            speed=request_data.speed
        )

        return {"success": True, "data": audio_data}

    except Exception as e:
        return {"success": False, "error": f"TTS生成失败: {str(e)}"}


@app.get("/api/v1/tts/voices")
async def get_available_voices():
    """
    获取可用的发音类型

    Returns:
        JSON: 发音类型列表
    """
    voices = []
    for voice_id, config in VOICE_CONFIGS.items():
        voices.append({
            "id": voice_id,
            "name": config["name"],
            "language": config["language"],
            "gender": config["gender"]
        })

    return {
        "success": True,
        "data": {
            "voices": voices
        }
    }


@app.get("/api/v1/tts/test")
async def test_tts_connection():
    """
    测试TTS服务连接

    Returns:
        JSON: 测试结果
    """
    try:
        tts_service = get_tts_service()
        is_connected = tts_service.test_connection()
        return {
            "success": True,
            "data": {
                "connected": is_connected,
                "service": "volcengine-tts"
            }
        }
    except Exception as e:
        return {"success": False, "error": f"TTS服务连接失败: {str(e)}"}


# ==================== History Management Routes ====================
@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """历史记录页面"""
    return templates.TemplateResponse(
        "history.html",
        {"request": request}
    )


class HistoryListResponse(BaseModel):
    """历史记录列表响应"""
    items: list
    total: int
    page: int
    limit: int
    has_next: bool
    has_prev: bool


@app.get("/api/v1/homework/history")
async def get_homework_history(
    page: int = 1,
    limit: int = 20,
    topic_filter: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    获取用户的作业历史记录

    Args:
        page: 页码（从1开始）
        limit: 每页数量（默认20）
        topic_filter: 主题过滤（可选）
        date_from: 开始日期（YYYY-MM-DD，可选）
        date_to: 结束日期（YYYY-MM-DD，可选）
        current_user: 当前用户（从JWT token解析）

    Returns:
        JSON: 作业列表、分页信息
    """
    session = next(get_session())

    try:
        # 构建查询
        query = select(HomeworkItem).where(HomeworkItem.user_id == current_user.user_id)

        # 应用主题过滤
        if topic_filter:
            query = query.where(HomeworkItem.topic.ilike(f"%{topic_filter}%"))

        # 应用日期过滤
        if date_from:
            try:
                from datetime import datetime
                dt_from = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.where(HomeworkItem.created_at >= dt_from)
            except ValueError:
                return {"success": False, "error": "开始日期格式错误，请使用 YYYY-MM-DD"}

        if date_to:
            try:
                from datetime import datetime, timedelta
                dt_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
                query = query.where(HomeworkItem.created_at < dt_to)
            except ValueError:
                return {"success": False, "error": "结束日期格式错误，请使用 YYYY-MM-DD"}

        # 排序：最新优先
        query = query.order_by(HomeworkItem.created_at.desc())

        # 计算总数
        from sqlalchemy import func
        count_query = select(func.count()).select_from(query.subquery())
        total_result = session.execute(count_query).scalar()
        total = total_result or 0

        # 应用分页
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        # 执行查询
        homeworks = session.exec(query).all()

        # 构建响应数据
        items = []
        for hw in homeworks:
            item = {
                "id": hw.id,
                "short_id": hw.short_id,
                "title": hw.title,
                "homework_type": hw.homework_type,
                "grade": hw.grade,
                "topic": hw.topic,
                "difficulty": hw.difficulty,
                "question_types": hw.question_types,
                "created_at": hw.created_at.isoformat(),
                "view_url": f"{settings.base_url}/v/{hw.short_id}"
            }

            # 如果是AI生成，解析题型统计
            if hw.homework_type == "ai_generated" and hw.question_types:
                try:
                    import json
                    types = json.loads(hw.question_types)
                    type_names = {
                        "choice": "选择题",
                        "fill_blank": "填空题",
                        "true_false": "判断题",
                        "reading": "阅读理解",
                        "listening": "听力题",
                        "essay": "作文"
                    }
                    type_labels = [f"{type_names.get(t['type'], t['type'])}×{t['count']}" for t in types]
                    item["question_types_label"] = " + ".join(type_labels)
                except:
                    item["question_types_label"] = "未知题型"
            else:
                item["question_types_label"] = "手动输入"

            items.append(item)

        return {
            "success": True,
            "data": {
                "items": items,
                "total": total,
                "page": page,
                "limit": limit,
                "has_next": offset + limit < total,
                "has_prev": page > 1
            }
        }

    except Exception as e:
        return {"success": False, "error": f"获取历史记录失败: {str(e)}"}


@app.get("/api/v1/homework/{homework_id}")
async def get_homework_details(
    homework_id: int,
    current_user = Depends(get_current_user)
):
    """
    获取单个作业详情

    Args:
        homework_id: 作业ID
        current_user: 当前用户（从JWT token解析）

    Returns:
        JSON: 作业详情
    """
    session = next(get_session())

    try:
        homework = session.get(HomeworkItem, homework_id)

        if not homework:
            return {"success": False, "error": "作业不存在"}

        # 验证所有权
        if homework.user_id != current_user.user_id:
            return {"success": False, "error": "无权访问此作业"}

        # 如果是AI生成，解析content
        content_data = homework.content
        if homework.homework_type == "ai_generated":
            try:
                import json
                content_data = json.loads(homework.content)
            except:
                pass

        return {
            "success": True,
            "data": {
                "id": homework.id,
                "short_id": homework.short_id,
                "title": homework.title,
                "content": content_data,
                "homework_type": homework.homework_type,
                "grade": homework.grade,
                "topic": homework.topic,
                "difficulty": homework.difficulty,
                "question_types": homework.question_types,
                "created_at": homework.created_at.isoformat(),
                "view_url": f"{settings.base_url}/v/{homework.short_id}",
                "audio_path": homework.audio_path,
                "audio_filename": homework.audio_filename
            }
        }

    except Exception as e:
        return {"success": False, "error": f"获取作业详情失败: {str(e)}"}


@app.delete("/api/v1/homework/{homework_id}")
async def delete_homework_endpoint(
    homework_id: int,
    current_user = Depends(get_current_user)
):
    """
    删除作业

    Args:
        homework_id: 作业ID
        current_user: 当前用户（从JWT token解析）

    Returns:
        JSON: 删除结果
    """
    session = next(get_session())

    try:
        homework = session.get(HomeworkItem, homework_id)

        if not homework:
            return {"success": False, "error": "作业不存在"}

        # 验证所有权
        if homework.user_id != current_user.user_id:
            return {"success": False, "error": "无权删除此作业"}

        # 删除作业
        delete_homework(session, homework_id)

        return {
            "success": True,
            "data": {
                "message": "作业已删除",
                "homework_id": homework_id
            }
        }

    except Exception as e:
        return {"success": False, "error": f"删除作业失败: {str(e)}"}


# ==================== Payment Routes ====================
@app.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request):
    """定价页面"""
    return templates.TemplateResponse(
        "pricing.html",
        {"request": request}
    )


class CreateOrderRequest(BaseModel):
    """创建订单请求"""
    order_type: str  # 'package' or 'subscription'


@app.post("/api/v1/payment/create-order")
async def create_payment_order(
    request_data: CreateOrderRequest,
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    创建支付订单

    Args:
        request_data: 订单类型（package/subscription）
        request: FastAPI Request对象（获取客户端IP）
        current_user: 当前用户

    Returns:
        JSON: 订单信息和支付参数
    """
    # 验证订单类型
    if request_data.order_type not in ["package", "subscription"]:
        return {"success": False, "error": "无效的订单类型"}

    # 获取客户端IP
    client_ip = request.client.host if request.client else "127.0.0.1"

    session = next(get_session())

    try:
        from payment_service import get_payment_service
        payment_service = get_payment_service()

        success, message, result = payment_service.create_order(
            session=session,
            user_id=current_user.user_id,
            order_type=request_data.order_type,
            client_ip=client_ip
        )

        if success:
            return {
                "success": True,
                "data": result,
                "message": message
            }
        else:
            return {"success": False, "error": message}

    except Exception as e:
        return {"success": False, "error": f"创建订单失败: {str(e)}"}


@app.post("/api/v1/payment/callback")
async def payment_callback(request: Request):
    """
    微信支付回调

    Args:
        request: FastAPI Request对象

    Returns:
        XML: 微信支付要求的响应格式
    """
    # 获取XML数据
    xml_data = await request.body()

    session = next(get_session())

    try:
        from payment_service import get_payment_service
        payment_service = get_payment_service()

        # 验证回调
        success, message, data = payment_service.verify_callback(xml_data)

        if not success:
            # 返回失败响应
            return Response(
                content="<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[{msg}]]></return_msg></xml>".format(msg=message),
                media_type="application/xml"
            )

        # 处理支付成功
        order_no = data.get("out_trade_no")
        transaction_id = data.get("transaction_id")

        success, message = payment_service.process_payment_success(
            session=session,
            order_no=order_no,
            transaction_id=transaction_id
        )

        if success:
            # 返回成功响应
            return Response(
                content="<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>",
                media_type="application/xml"
            )
        else:
            # 返回失败响应
            return Response(
                content="<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[{msg}]]></return_msg></xml>".format(msg=message),
                media_type="application/xml"
            )

    except Exception as e:
        # 返回失败响应
        return Response(
            content="<xml><return_code><![CDATA[FAIL]]></return_msg><return_msg><![CDATA[{error}]]></return_msg></xml>".format(error=str(e)),
            media_type="application/xml"
        )


@app.get("/api/v1/payment/orders")
async def get_user_payment_orders(
    limit: int = 20,
    current_user = Depends(get_current_user)
):
    """
    获取用户的支付订单列表

    Args:
        limit: 返回数量限制
        current_user: 当前用户

    Returns:
        JSON: 订单列表
    """
    session = next(get_session())

    try:
        from payment_service import get_payment_service
        payment_service = get_payment_service()

        orders = payment_service.get_user_orders(
            session=session,
            user_id=current_user.user_id,
            limit=limit
        )

        return {
            "success": True,
            "data": {
                "orders": orders
            }
        }

    except Exception as e:
        return {"success": False, "error": f"获取订单列表失败: {str(e)}"}


@app.get("/api/v1/payment/check-status/{order_no}")
async def check_order_status(
    order_no: str,
    current_user = Depends(get_current_user)
):
    """
    查询订单状态

    Args:
        order_no: 订单号
        current_user: 当前用户

    Returns:
        JSON: 订单状态
    """
    session = next(get_session())

    # 验证订单所有权
    order = session.exec(
        select(Order).where(Order.order_no == order_no)
    ).first()

    if not order:
        return {"success": False, "error": "订单不存在"}

    if order.user_id != current_user.user_id:
        return {"success": False, "error": "无权访问此订单"}

    try:
        from payment_service import get_payment_service
        payment_service = get_payment_service()

        # 查询微信支付订单状态
        success, message, wechat_data = payment_service.query_order(order_no)

        if success and wechat_data:
            # 如果微信返回已支付，但本地未更新，则更新本地状态
            if wechat_data.get("trade_state") == "SUCCESS" and order.status != "paid":
                payment_service.process_payment_success(
                    session=session,
                    order_no=order_no,
                    transaction_id=wechat_data.get("transaction_id", "")
                )

        return {
            "success": True,
            "data": {
                "order_no": order.order_no,
                "type": order.type,
                "amount": order.amount,
                "status": order.status,
                "created_at": order.created_at.isoformat(),
                "paid_at": order.paid_at.isoformat() if order.paid_at else None
            }
        }

    except Exception as e:
        return {"success": False, "error": f"查询订单状态失败: {str(e)}"}


@app.get("/api/v1/payment/test")
async def test_payment_service():
    """
    测试支付服务连接

    Returns:
        JSON: 测试结果
    """
    try:
        from payment_service import get_payment_service, PaymentConfig
        payment_service = get_payment_service()

        config = PaymentConfig()

        return {
            "success": True,
            "data": {
                "configured": payment_service.test_connection(),
                "package_price": config.PACKAGE_PRICE / 100,  # 转换为元
                "monthly_price": config.MONTHLY_PRICE / 100,
                "package_count": config.PACKAGE_COUNT,
                "monthly_days": config.MONTHLY_DAYS
            }
        }
    except Exception as e:
        return {"success": False, "error": f"测试失败: {str(e)}"}



# ==================== Main Page ====================
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页 - 二维码生成器"""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": "EduQR Lite",
            "default_size": settings.qr_code_size,
            "default_error_correction": settings.qr_error_correction,
            "max_upload_size_mb": settings.max_upload_size_mb,
            "allowed_extensions": settings.allowed_audio_extensions
        }
    )


# ==================== View Homework (Student) ====================
@app.get("/v/{short_id}", response_class=HTMLResponse)
async def view_homework(request: Request, short_id: str):
    """查看作业（学生扫码后跳转的页面）"""
    session = next(get_session())
    homework = get_homework_by_short_id(session, short_id)

    if not homework:
        return templates.TemplateResponse(
            "view.html",
            {
                "request": request,
                "error": "作业不存在或已过期",
                "short_id": short_id
            },
            status_code=404
        )

    # 渲染 Markdown 内容
    rendered_content = render_markdown(homework.content)
    title = homework.title or extract_title(homework.content)

    return templates.TemplateResponse(
        "view.html",
        {
            "request": request,
            "homework": homework,
            "title": title,
            "rendered_content": rendered_content,
            "formatted_time": format_timestamp(homework.created_at),
            "formatted_audio_size": format_file_size(homework.audio_size) if homework.audio_size else None
        }
    )


# ==================== API Routes ====================
@app.post("/api/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    """
    上传音频文件

    Returns:
        JSON: 文件信息（filename, path, size, url）
    """
    # 验证文件大小
    content = await file.read()
    file_size = len(content)

    # 重置文件指针
    await file.seek(0)

    # 验证文件
    is_valid, error_msg = validate_audio_file(
        file.filename,
        file_size,
        settings.max_upload_size_mb,
        settings.allowed_extensions_list
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # 生成文件路径（按日期组织）
    date_path = datetime.now().strftime("%Y/%m")
    filename = f"{generate_short_id(12)}_{file.filename}"
    relative_path = f"{date_path}/{filename}"
    full_path = UPLOAD_DIR / date_path
    full_path.mkdir(parents=True, exist_ok=True)

    file_path = full_path / filename

    # 保存文件
    with open(file_path, "wb") as f:
        f.write(content)

    # 返回文件信息
    file_url = f"{settings.base_url}/static/uploads/{relative_path}"

    return {
        "success": True,
        "filename": file.filename,
        "path": relative_path,
        "size": file_size,
        "url": file_url
    }


@app.post("/api/generate")
async def generate_qrcode(
    request: Request,
    content: str = Form(""),
    mode: str = Form("static"),
    access_code: str = Form(""),
    size: int = Form(settings.qr_code_size),
    error_correction: str = Form(settings.qr_error_correction),
    audio_filename: Optional[str] = Form(None),
    audio_path: Optional[str] = Form(None),
    audio_size: Optional[int] = Form(None),
):
    """
    生成二维码

    Args:
        content: 作业内容
        mode: 模式 ('static', 'text', 'listening')
        access_code: 管理暗号
        size: 二维码尺寸
        error_correction: 容错率
        audio_filename: 音频文件名（听力模式）
        audio_path: 音频文件路径
        audio_size: 音频文件大小

    Returns:
        JSON: 二维码数据（Base64）和短 ID（活码模式）
    """
    # 验证管理暗号
    if access_code != settings.admin_password:
        raise HTTPException(status_code=403, detail="暗号错误，请联系教师获取")

    # 验证内容（Form 参数为空时会是空字符串，不是 None）
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")

    # 验证长度
    is_valid, error_msg = validate_content_length(content, settings.max_content_length)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # 生成二维码
    if mode == "static":
        # 静态码：直接编码文本
        qr_data_url = generate_qr_code(content, size, error_correction)
        return {
            "success": True,
            "mode": "static",
            "qr_code_data_url": qr_data_url,
            "short_id": None
        }

    else:
        # 活码模式：保存到数据库，生成 URL
        session = next(get_session())

        # 生成短 ID
        max_retries = 5
        for _ in range(max_retries):
            short_id = generate_short_id(8)
            existing = get_homework_by_short_id(session, short_id)
            if not existing:
                break
        else:
            raise HTTPException(status_code=500, detail="生成短 ID 失败，请重试")

        # 提取标题
        title = extract_title(content)

        # 保存到数据库
        homework_type = "listening" if mode == "listening" else "text"
        save_homework(
            session,
            short_id=short_id,
            content=content,
            title=title,
            audio_path=audio_path,
            audio_filename=audio_filename,
            audio_size=audio_size,
            homework_type=homework_type
        )

        # 生成活码 URL
        view_url = f"{settings.base_url}/v/{short_id}"
        qr_data_url = generate_qr_code(view_url, size, error_correction)

        return {
            "success": True,
            "mode": mode,
            "qr_code_data_url": qr_data_url,
            "short_id": short_id,
            "view_url": view_url
        }


@app.get("/api/homework/{short_id}")
async def find_homework(short_id: str, access_code: str):
    """
    查找活码记录（编辑前查询）

    Args:
        short_id: 作业短 ID（访问码）
        access_code: 管理暗号

    Returns:
        JSON: 作业内容信息
    """
    if access_code != settings.admin_password:
        raise HTTPException(status_code=403, detail="暗号错误，请联系教师获取")

    session = next(get_session())
    homework = get_homework_by_short_id(session, short_id)

    if not homework:
        raise HTTPException(status_code=404, detail="未找到该访问码对应的作业")

    if homework.homework_type == "static":
        raise HTTPException(
            status_code=400,
            detail="静态码内容编码在二维码本身中，无法修改"
        )

    return {
        "success": True,
        "data": {
            "short_id": homework.short_id,
            "content": homework.content,
            "title": homework.title,
            "homework_type": homework.homework_type,
            "audio_path": homework.audio_path,
            "audio_filename": homework.audio_filename,
            "audio_size": homework.audio_size,
            "created_at": homework.created_at.isoformat(),
            "view_url": f"{settings.base_url}/v/{homework.short_id}"
        }
    }


@app.put("/api/homework/{short_id}")
async def update_homework_endpoint(
    short_id: str,
    access_code: str = Form(""),
    content: str = Form(""),
    audio_filename: Optional[str] = Form(None),
    audio_path: Optional[str] = Form(None),
    audio_size: Optional[int] = Form(None),
):
    """
    更新活码作业内容

    Args:
        short_id: 作业短 ID
        access_code: 管理暗号
        content: 新的作业内容
        audio_filename: 新音频文件名（可选）
        audio_path: 新音频路径（可选）
        audio_size: 新音频大小（可选）

    Returns:
        JSON: 更新结果
    """
    if access_code != settings.admin_password:
        raise HTTPException(status_code=403, detail="暗号错误，请联系教师获取")

    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")

    is_valid, error_msg = validate_content_length(content, settings.max_content_length)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    session = next(get_session())
    homework = get_homework_by_short_id(session, short_id)

    if not homework:
        raise HTTPException(status_code=404, detail="未找到该访问码对应的作业")

    if homework.homework_type == "static":
        raise HTTPException(
            status_code=400,
            detail="静态码内容编码在二维码本身中，无法修改"
        )

    # 如果上传了新音频且旧音频存在，删除旧音频文件
    if audio_path and homework.audio_path and audio_path != homework.audio_path:
        try:
            old_file = UPLOAD_DIR / homework.audio_path
            if old_file.exists():
                old_file.unlink()
        except Exception as e:
            print(f"Warning: failed to delete old audio file: {e}")

    title = extract_title(content)

    updated = update_homework(
        session,
        short_id=short_id,
        content=content,
        title=title,
        audio_path=audio_path,
        audio_filename=audio_filename,
        audio_size=audio_size,
    )

    if not updated:
        raise HTTPException(status_code=500, detail="更新失败，请重试")

    return {
        "success": True,
        "data": {
            "short_id": updated.short_id,
            "view_url": f"{settings.base_url}/v/{updated.short_id}"
        }
    }


@app.get("/api/stats")
async def get_stats(access_code: str):
    """
    获取统计信息（需验证暗号）
    """
    if access_code != settings.admin_password:
        raise HTTPException(status_code=403, detail="暗号错误")

    session = next(get_session())
    total_count = len(list(session.exec(select(HomeworkItem)).all()))

    # 计算上传文件总大小
    uploads_size = sum(
        f.stat().st_size for f in UPLOAD_DIR.rglob('*') if f.is_file()
    )

    return {
        "success": True,
        "total_homeworks": total_count,
        "uploads_size_bytes": uploads_size,
        "uploads_size_formatted": format_file_size(uploads_size)
    }


# ==================== Error Handlers ====================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """统一错误处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
