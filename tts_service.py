"""
TTS服务层 - 火山引擎集成
"""
import os
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from volcengine.Api import  Api as TtsApi
from pathlib import Path


class VolcengineTTSService:
    """火山引擎TTS服务类"""

    def __init__(
        self,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None
    ):
        """
        初始化火山引擎TTS服务

        Args:
            access_key: 访问密钥，如果不提供则从环境变量读取
            secret_key: 秘密密钥，如果不提供则从环境变量读取
        """
        self.access_key = access_key or os.getenv("VOLCENGINE_ACCESS_KEY")
        self.secret_key = secret_key or os.getenv("VOLCENGINE_SECRET_KEY")

        if not self.access_key or not self.secret_key:
            raise ValueError("VOLCENGINE_ACCESS_KEY or VOLCENGINE_SECRET_KEY not found in environment variables")

        # 创建TTS API实例
        self.tts_api = TtsApi()

        # 音频存储目录
        self.storage_dir = Path(os.getenv("UPLOAD_DIR", "static/tts"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 按日期组织文件
        self.date_path = datetime.now().strftime("%Y/%m")

    def generate_audio(
        self,
        text: str,
        voice: str = "en_us_male",
        speed: float = 1.0,
        output_format: str = "mp3"
    ) -> Dict[str, Any]:
        """
        生成TTS音频

        Args:
            text: 要转换的文本
            voice: 发音类型
                - en_us_male: 美式男声
                - en_us_female: 美式女声
                - en_gb_male: 英式男声
                - en_gb_female: 英式女声
            speed: 语速（0.8-1.2）
            output_format: 输出格式（mp3/wav）

        Returns:
            dict: {
                "success": True,
                "audio_url": "/static/tts/2024/02/audio_xxx.mp3",
                "audio_path": "2024/02/audio_xxx.mp3",
                "duration": 5.2,
                "file_size": 12345
            }
        """
        try:
            # 构建请求参数
            req = {
                "app": {
                    "appid": "your_appid",  # 需要从火山引擎获取
                    "token": "your_token",    # 需要从火山引擎获取
                    "cluster": "volcano_tts"
                },
                "user": {
                    "uid": "user_001"
                },
                "audio": {
                    "voice_type": voice,
                    "encoding": "utf-8",
                    "speed": speed,
                    "volume": 1.0,
                    "pitch": 1.0,
                },
                "request": {
                    "reqid": str(uuid.uuid4()),
                    "text": text,
                    "text_type": "plain",
                    "operation": "query"
                }
            }

            # 调用火山引擎TTS API
            # 注意：这里是简化实现，实际需要根据火山引擎SDK文档调整
            resp = self.tts_api.send_request(
                "https://openspeech.bytedance.com/api/v1/tts",
                "POST",
                req
            )

            # 解析响应
            if resp.get("code") != 0:
                raise Exception(f"TTS API error: {resp.get('message', 'Unknown error')}")

            # 保存音频文件
            audio_data = resp.get("data", "")
            if not audio_data:
                raise Exception("No audio data returned")

            # 生成文件名
            filename = f"tts_{uuid.uuid4().hex[:12]}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{output_format}"
            relative_path = f"{self.date_path}/{filename}"
            full_path = self.storage_dir / self.date_path
            full_path.mkdir(parents=True, exist_ok=True)
            file_path = full_path / filename

            # 写入音频文件
            with open(file_path, "wb") as f:
                f.write(audio_data)

            # 获取音频时长（简化处理，实际应该从响应中获取）
            duration = len(text) * 0.1  # 估算：每个字符约0.1秒

            # 获取文件大小
            file_size = len(audio_data)

            return {
                "success": True,
                "audio_url": f"/static/tts/{relative_path}",
                "audio_path": relative_path,
                "duration": duration,
                "file_size": file_size
            }

        except Exception as e:
            raise Exception(f"TTS生成失败: {str(e)}")

    def generate_multiple_audio(
        self,
        texts: list,
        voice: str = "en_us_male",
        speed: float = 1.0
    ) -> list:
        """
        批量生成TTS音频

        Args:
            texts: 文本列表
            voice: 发音类型
            speed: 语速

        Returns:
            list: 音频信息列表
        """
        results = []
        for text in texts:
            try:
                result = self.generate_audio(text, voice, speed)
                results.append(result)
            except Exception as e:
                print(f"生成音频失败: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "text": text[:50] + "..." if len(text) > 50 else text
                })
        return results

    def test_connection(self) -> bool:
        """
        测试API连接

        Returns:
            bool: 连接是否成功
        """
        try:
            result = self.generate_audio("Hello, this is a test.", "en_us_male", 1.0)
            return result.get("success", False)
        except Exception as e:
            print(f"TTS连接测试失败: {e}")
            return False


# ==================== 发音配置 ====================
VOICE_CONFIGS = {
    "en_us_male": {
        "name": "美式男声",
        "id": "zh_male",  # 火山引擎的实际voice_type，需要根据文档调整
        "language": "en-US",
        "gender": "male"
    },
    "en_us_female": {
        "name": "美式女声",
        "id": "zh_female",
        "language": "en-US",
        "gender": "female"
    },
    "en_gb_male": {
        "name": "英式男声",
        "id": "en_male",
        "language": "en-GB",
        "gender": "male"
    },
    "en_gb_female": {
        "name": "英式女声",
        "id": "en_female",
        "language": "en-GB",
        "gender": "female"
    }
}

# ==================== 语速配置 ====================
SPEED_CONFIGS = {
    "slow": 0.8,
    "normal": 1.0,
    "fast": 1.2
}

# ==================== 单例模式 ====================
_tts_service: Optional[VolcengineTTSService] = None


def get_tts_service() -> VolcengineTTSService:
    """
    获取TTS服务实例（单例模式）

    Returns:
        VolcengineTTSService: TTS服务实例
    """
    global _tts_service
    if _tts_service is None:
        _tts_service = VolcengineTTSService()
    return _tts_service


# ==================== 辅助函数 ====================
def validate_tts_params(
    text: str,
    voice: str,
    speed: float
) -> tuple[bool, str]:
    """
    验证TTS参数

    Args:
        text: 要转换的文本
        voice: 发音类型
        speed: 语速

    Returns:
        tuple[bool, str]: (是否有效, 错误信息)
    """
    # 验证文本
    if not text or len(text.strip()) < 1:
        return False, "文本不能为空"

    if len(text) > 5000:
        return False, "文本长度不能超过5000个字符"

    # 验证发音
    if voice not in VOICE_CONFIGS:
        valid_voices = ", ".join(VOICE_CONFIGS.keys())
        return False, f"无效的发音类型，必须是: {valid_voices}"

    # 验证语速
    if speed < 0.5 or speed > 2.0:
        return False, "语速必须在0.5-2.0之间"

    return True, ""
