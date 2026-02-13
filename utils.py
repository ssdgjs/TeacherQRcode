"""
工具函数 - 二维码生成、短 ID 生成、Markdown 渲染
"""
import qrcode
from io import BytesIO
import base64
import secrets
import string
import re
from datetime import datetime
import markdown
from typing import Tuple


# ==================== Short ID Generator ====================
def generate_short_id(length: int = 8) -> str:
    """
    生成随机短 ID

    Args:
        length: ID 长度，默认 8 位

    Returns:
        随机短 ID（字母+数字）
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# ==================== QR Code Generator ====================
def generate_qr_code(
    content: str,
    size: int = 300,
    error_correction: str = "M",
    border: int = 4
) -> str:
    """
    生成二维码并返回 Base64 编码的 PNG 图片

    Args:
        content: 二维码内容（文本或 URL）
        size: 二维码尺寸（像素）
        error_correction: 容错率 (L/M/Q/H)
        border: 边框大小

    Returns:
        Base64 编码的 PNG 图片数据（data URL 格式）
    """
    # 容错率映射
    error_levels = {
        "L": qrcode.constants.ERROR_CORRECT_L,  # 7%
        "M": qrcode.constants.ERROR_CORRECT_M,  # 15%
        "Q": qrcode.constants.ERROR_CORRECT_Q,  # 25%
        "H": qrcode.constants.ERROR_CORRECT_H   # 30%
    }

    # 创建 QR Code 实例
    qr = qrcode.QRCode(
        version=1,
        error_correction=error_levels.get(error_correction, qrcode.constants.ERROR_CORRECT_M),
        box_size=max(1, size // 25),  # 自动计算 box_size
        border=border,
    )

    qr.add_data(content)
    qr.make(fit=True)

    # 生成图片
    img = qr.make_image(fill_color="black", back_color="white")

    # 调整尺寸到指定大小
    if img.size != (size, size):
        img = img.resize((size, size))

    # 转换为 Base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()

    return f"data:image/png;base64,{img_str}"


# ==================== Content Processing ====================
def extract_title(content: str, max_length: int = 30) -> str:
    """
    从内容中提取标题

    Args:
        content: 作业内容
        max_length: 标题最大长度

    Returns:
        提取的标题
    """
    # 移除 Markdown 标记
    lines = content.strip().split('\n')
    first_line = lines[0].strip()

    # 移除 # 标记
    first_line = re.sub(r'^#+\s*', '', first_line)

    # 截断过长标题
    if len(first_line) > max_length:
        return first_line[:max_length] + "..."

    return first_line if first_line else "今日作业"


def render_markdown(content: str) -> str:
    """
    渲染 Markdown 为 HTML（基础语法）

    Args:
        content: Markdown 文本

    Returns:
        HTML 字符串
    """
    # 配置 Markdown 扩展
    md = markdown.Markdown(extensions=[
        'nl2br',     # 换行符转 <br>
        'fenced_code',  # 代码块
    ])

    html = md.convert(content)

    return html


def sanitize_markdown(content: str) -> str:
    """
    简单的 Markdown 清理（移除不安全的内容）

    Args:
        content: 原始内容

    Returns:
        清理后的内容
    """
    # 移除 HTML 标签（防止 XSS）
    content = re.sub(r'<[^>]+>', '', content)

    # 移除 JavaScript 协议
    content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)

    return content


def calculate_reading_time(content: str) -> int:
    """
    估算阅读时间（分钟）

    Args:
        content: 文本内容

    Returns:
        阅读时间（分钟）
    """
    # 中文按 400 字/分钟，英文按 200 词/分钟
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
    english_words = len(re.findall(r'\b[a-zA-Z]+\b', content))

    minutes = (chinese_chars / 400) + (english_words / 200)
    return max(1, int(minutes) + (1 if minutes % 1 > 0.5 else 0))


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小

    Args:
        size_bytes: 字节数

    Returns:
        格式化的大小字符串（如 "3.2 MB"）
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def format_timestamp(dt: datetime) -> str:
    """
    格式化时间戳

    Args:
        dt: datetime 对象

    Returns:
        格式化的时间字符串（如 "2026年2月8日 发布"）
    """
    return dt.strftime("%Y年%m月%d日 发布")


# ==================== Validation ====================
def validate_content_length(content: str, max_length: int = 10000) -> Tuple[bool, str]:
    """
    验证内容长度

    Args:
        content: 内容文本
        max_length: 最大长度

    Returns:
        (是否有效, 错误消息)
    """
    if len(content) > max_length:
        return False, f"内容过长，最多支持 {max_length} 字符"
    # 空内容检查在调用前处理
    return True, ""


def validate_audio_file(filename: str, size: int, max_size_mb: int = 20, allowed_extensions: list = None) -> Tuple[bool, str]:
    """
    验证音频文件

    Args:
        filename: 文件名
        size: 文件大小（字节）
        max_size_mb: 最大大小（MB）
        allowed_extensions: 允许的扩展名列表

    Returns:
        (是否有效, 错误消息)
    """
    if allowed_extensions is None:
        allowed_extensions = ['mp3', 'wav', 'm4a', 'ogg']

    # 检查扩展名
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in allowed_extensions:
        return False, f"不支持的文件格式，请使用：{', '.join(allowed_extensions)}"

    # 检查大小
    max_size_bytes = max_size_mb * 1024 * 1024
    if size > max_size_bytes:
        return False, f"文件过大，最大支持 {max_size_mb}MB"

    return True, ""


def get_recommended_mode(content: str, has_audio: bool = False) -> str:
    """
    根据内容推荐模式

    Args:
        content: 内容文本
        has_audio: 是否包含音频

    Returns:
        推荐的模式 ('static', 'text', 'listening')
    """
    if has_audio:
        return "listening"

    if len(content) <= 300:
        return "static"

    return "text"
