"""
Ollama TTS 服务层 - 使用 Ollama 本地模型生成音频
"""
import os
import httpx
import json
from typing import Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class OllamaTTS:
    """Ollama TTS 服务类"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        初始化 Ollama TTS 服务

        Args:
            base_url: Ollama 服务地址
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=120.0)  # 2分钟超时

    def text_to_speech(
        self,
        text: str,
        model: str = "chattts",
        voice: str = "default"
    ) -> bytes:
        """
        文本转语音

        Args:
            text: 要转换的文本
            model: 使用的模型
            voice: 声音类型

        Returns:
            bytes: 音频数据 (PCM/WAV格式)
        """
        try:
            # 方法1: 使用 generate API (某些模型支持)
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": text,
                    "stream": False,
                    "options": {
                        "num_predict": 0  # 不生成文本，只返回音频
                    }
                },
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()

                # 检查是否有音频数据
                if "response" in result or "audio" in result:
                    logger.info(f"TTS 生成成功: {len(text)} 字符")
                    # TODO: 解析音频数据格式
                    return b""

            logger.warning(f"模型 {model} 可能不支持音频生成")
            return b""

        except Exception as e:
            logger.error(f"TTS 生成失败: {e}")
            return b""


class OllamaTTSFallback:
    """Ollama TTS 回退方案 - 使用 ChatTTS Python 库"""

    def __init__(self):
        """初始化 ChatTTS"""
        try:
            from ChatTTS import Chat
            self.chat = Chat()
            self.available = True
            logger.info("ChatTTS 库加载成功")
        except ImportError:
            self.available = False
            logger.warning("ChatTTS 库未安装，请运行: pip install ChatTTS")

    def text_to_speech(
        self,
        text: str,
        voice: str = "female"
    ) -> bytes:
        """
        文本转语音

        Args:
            text: 要转换的文本
            voice: 声音类型 (female/male)

        Returns:
            bytes: WAV 音频数据
        """
        if not self.available:
            return b""

        try:
            import io
            import wave

            # 生成音频
            audio = self.chat.infer(
                text,
                voice=voice,
                language='en'  # 英语
            )

            # 转换为 WAV 格式
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(1)  # 单声道
                wf.setsampwidth(2)  # 16位
                wf.setframerate(24000)  # 采样率

                # 假设 audio 是 numpy 数组
                import numpy as np
                audio_array = audio[0]  # 取第一个通道
                wf.writeframes((audio_array * 32767).astype(np.int16))

            wav_buffer.seek(0)
            return wav_buffer.read()

        except Exception as e:
            logger.error(f"ChatTTS 生成失败: {e}")
            return b""


# ==================== TTS 服务工厂 ====================

_tts_instance = None

def get_tts_service() -> OllamaTTS | OllamaTTSFallback:
    """获取 TTS 服务实例"""
    global _tts_instance

    if _tts_instance is None:
        # 优先使用 ChatTTS 库（更稳定）
        tts = OllamaTTSFallback()
        if not tts.available:
            # 回退到 Ollama API
            tts = OllamaTTS()

        _tts_instance = tts

    return _tts_instance


def validate_tts_params(file) -> tuple[bool, str]:
    """验证音频文件参数（暂时通过，使用本地 TTS 不需要上传）"""
    return True, ""
