"""
本地 TTS 服务 - 支持多说话者对话合成
"""
import os
import subprocess
import tempfile
import logging
import re
from pathlib import Path
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


# 扩展的说话者声音映射（按角色特征分类）
SPEAKER_VOICES = {
    # === 成年男性 ===
    "M_Adult_Deep": "en-US-GuyNeural",           # 深沉男声
    "M_Adult_Warm": "en-US-ChristopherNeural",   # 温暖男声
    "M_Adult_Professional": "en-US-BrianNeural", # 专业男声

    # === 成年女性 ===
    "W_Adult_Calm": "en-US-AriaNeural",          # 冷静女声
    "W_Adult_Friendly": "en-US-JennyNeural",     # 友善女声
    "W_Adult_Professional": "en-US-MichelleNeural", # 专业女声

    # === 年轻男性（学生/青少年）===
    "M_Young_Casual": "en-US-EricNeural",        # 随意年轻男声
    "M_Young_Energetic": "en-US-JasonNeural",    # 活力年轻男声

    # === 年轻女性（学生/青少年）===
    "W_Young_Casual": "en-US-MichelleNeural",    # 随意年轻女声
    "W_Young_Sweet": "en-US-AriaNeural",         # 甜美年轻女声
}

# 对话主题与角色关系映射
CONTEXT_PATTERNS = {
    "school": {
        "keywords": ["class", "teacher", "student", "homework", "school", "exam", "lesson", "mr.", "ms.", "professor", "finish", "easy", "learn"],
        "default_roles": ("M_Young", "W_Young"),  # 同学之间
        "teacher_patterns": ["teacher", "mr.", "ms.", "professor", "explained", "taught"],
    },
    "medical": {
        "keywords": ["doctor", "patient", "medicine", "hospital", "pain", "symptom", "fever", "headache"],
        "default_roles": ("M_Adult", "W_Adult"),  # 医生-病人
    },
    "shopping": {
        "keywords": ["buy", "sell", "price", "shop", "store", "how much", "dollars", "cashier"],
        "default_roles": ("M_Adult", "W_Adult"),  # 店员-顾客
    },
    "family": {
        "keywords": ["mom", "dad", "parent", "child", "son", "daughter", "home"],
        "default_roles": ("M_Adult", "W_Adult"),  # 父母-孩子
    },
    "restaurant": {
        "keywords": ["order", "menu", "waiter", "waitress", "food", "drink", "table"],
        "default_roles": ("M_Adult", "W_Adult"),  # 服务员-顾客
    },
}


class LocalTTSService:
    """本地 TTS 服务"""

    def __init__(self):
        """初始化 TTS 服务"""
        self.method = self._detect_method()
        logger.info(f"TTS 方法: {self.method}")

    def _detect_method(self) -> str:
        """检测可用的 TTS 方法"""
        # 方法1: ChatTTS Python 库
        try:
            import ChatTTS
            return "chatts_lib"
        except ImportError:
            pass

        # 方法2: edge-tts (微软免费)
        try:
            result = subprocess.run(
                ["edge-tts", "--version"],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                return "edge_tts"
        except:
            pass

        # 方法3: espeak (系统自带)
        try:
            result = subprocess.run(
                ["espeak", "--version"],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                return "espeak"
        except:
            pass

        return "none"

    def dialogue_to_speech(
        self,
        script: str,
        output_path: Optional[str] = None,
        voice_map: Optional[dict] = None
    ) -> tuple[bool, str, Optional[str]]:
        """
        对话脚本转语音（支持多说话者）

        解析格式：
        M: Hello, how are you?
        W: I'm fine, thank you.
        M: What's your name?
        W: My name is Mary.

        Args:
            script: 对话脚本
            output_path: 输出文件路径
            voice_map: 自定义说话者声音映射，如 {"M": "en-US-GuyNeural", "W": "en-US-AriaNeural"}

        Returns:
            tuple[bool, str, Optional[str]]: (是否成功, 消息, 文件路径)
        """
        try:
            if output_path is None:
                output_path = tempfile.mktemp(suffix=".mp3")

            # 解析对话脚本
            dialogue_parts = self._parse_dialogue(script)
            if not dialogue_parts:
                # 如果没有识别到对话格式，回退到普通 TTS
                logger.warning("未识别到对话格式，使用普通 TTS")
                return self.text_to_speech(script, output_path)

            # 检测对话语境，确定角色关系
            # 优先使用 AI 分析，失败则回退到规则匹配
            context = self._detect_context(script, dialogue_parts)
            logger.info(f"检测到对话语境: {context}")

            # 尝试使用 AI 分析角色
            speaker_profiles = self._analyze_characters_with_ai(dialogue_parts, context)
            if speaker_profiles:
                logger.info(f"AI 角色分析成功")
                speaker_voices = self._assign_voices_by_profiles(speaker_profiles)
            else:
                logger.info(f"AI 分析失败，使用规则匹配")
                # 根据语境和说话者标记分配声音
                speaker_voices = self._assign_voices_by_context(dialogue_parts, context, voice_map)
            logger.info(f"说话者声音映射: {speaker_voices}")

            # 优先使用 ChatTTS（如果可用）
            if self.method == "chatts_lib":
                return self._generate_with_chatts(dialogue_parts, speaker_voices, output_path)

            # 回退到 edge-tts
            return self._generate_with_edge_tts(dialogue_parts, speaker_voices, output_path)

        except Exception as e:
            logger.error(f"对话 TTS 失败: {e}")
            import traceback
            traceback.print_exc()
            return False, f"对话 TTS 失败: {str(e)}", None

    def _generate_with_chatts(
        self,
        dialogue_parts: List[Tuple[str, str]],
        speaker_voices: dict,
        output_path: str
    ) -> tuple[bool, str, Optional[str]]:
        """
        使用 ChatTTS 生成多说话者对话

        ChatTTS 0.2.4+ 使用 spk_emb 参数来区分不同说话者
        """
        try:
            from ChatTTS import Chat
            import torch
            import numpy as np
            import wave

            logger.info("使用 ChatTTS 生成多说话人音频")

            # 初始化 ChatTTS
            chat = Chat()

            # 加载本地模型（如果已下载）
            try:
                local_dir = "/Users/yangfan/Documents/coding/DownloadQRcode"
                if os.path.exists(local_dir):
                    success = chat.load(source='local', compile=False, device='cpu')
                    logger.info(f"ChatTTS 从本地加载: {'成功' if success else '失败'}")
                else:
                    success = chat.load(compile=False, device='cpu')
            except Exception as e:
                logger.warning(f"ChatTTS 加载失败: {e}，尝试使用默认方式")
                success = chat.load(compile=False, device='cpu')

            if not success:
                raise Exception("ChatTTS 模型加载失败")

            # 检测对话场景，调整生成参数
            # 重建完整脚本用于场景检测
            full_script = "\n".join([f"{s}: {t}" for s, t in dialogue_parts])
            context = self._detect_context(full_script, dialogue_parts)
            logger.info(f"检测到对话场景: {context}")

            # 根据场景设置生成参数
            scene_params = self._get_scene_params(context)

            # 获取所有唯一说话者
            speakers = list(set([speaker for speaker, _ in dialogue_parts]))
            logger.info(f"识别到 {len(speakers)} 个说话者: {speakers}")

            # 为每个说话者分配不同的说话人嵌入（spk_emb）
            speaker_embs = {}
            for i, speaker in enumerate(speakers):
                # 使用固定种子确保每次生成相同说话者有相同声音
                torch.manual_seed(1000 + i * 1000)
                spk_emb = chat.sample_random_speaker()
                speaker_embs[speaker] = spk_emb
                logger.info(f"说话者 {speaker} 分配 spk_emb (种子={1000 + i * 1000})")

            # 为每句对话生成音频
            all_segments = []
            for speaker, text in dialogue_parts:
                # 创建参数对象
                params = chat.InferCodeParams()

                # 设置说话人嵌入
                params.spk_emb = speaker_embs.get(speaker, speaker_embs[speakers[0]])

                # 应用场景参数
                params.temperature = scene_params['temperature']
                params.top_P = scene_params['top_P']
                params.top_K = scene_params['top_K']
                params.repetition_penalty = scene_params['repetition_penalty']

                # 可以根据说话者角色添加额外的风格调整
                if 'Adult' in speaker or 'Teacher' in speaker or 'Doctor' in speaker:
                    # 成年人/教师/医生：语速稍慢，更稳定
                    params.prompt = '[speed_5]'
                elif 'Child' in speaker or 'Student' in speaker:
                    # 儿童/学生：语速正常，活泼
                    params.prompt = '[speed_6]'

                try:
                    wavs = chat.infer(text, params_infer_code=params)
                    if wavs and len(wavs) > 0 and wavs[0] is not None:
                        all_segments.append(wavs[0])
                        logger.info(f"✅ 说话者 {speaker}: \"{text[:30]}...\" 音频生成成功")
                    else:
                        logger.warning(f"⚠️ 说话者 {speaker}: 音频生成返回空")
                except Exception as e:
                    logger.error(f"❌ 说话者 {speaker} 生成失败: {e}")
                    raise

            if not all_segments:
                raise Exception("ChatTTS 未生成任何音频")

            # 拼接所有音频片段
            logger.info(f"合并 {len(all_segments)} 段音频...")
            final_audio = np.concatenate(all_segments, axis=0)

            # 保存为 WAV 文件
            sample_rate = 24000  # ChatTTS 默认采样率
            if output_path.endswith('.mp3'):
                # 先保存为 WAV，然后转换为 MP3
                wav_path = output_path.replace('.mp3', '.wav')
                with wave.open(wav_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)

                    # 归一化并转换为 int16
                    audio_int16 = np.clip(final_audio, -1.0, 1.0)
                    audio_int16 = (audio_int16 * 32767).astype(np.int16)
                    wf.writeframes(audio_int16.tobytes())

                # 转换为 MP3
                import subprocess
                result = subprocess.run(
                    ['ffmpeg', '-y', '-i', wav_path, output_path],
                    capture_output=True,
                    timeout=30
                )

                # 删除临时 WAV 文件
                if os.path.exists(wav_path):
                    os.remove(wav_path)

                if result.returncode != 0:
                    logger.warning(f"ffmpeg 转换失败，使用 WAV 格式: {result.stderr.decode()}")
                    output_path = wav_path
            else:
                # 直接保存为 WAV
                with wave.open(output_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)

                    audio_int16 = np.clip(final_audio, -1.0, 1.0)
                    audio_int16 = (audio_int16 * 32767).astype(np.int16)
                    wf.writeframes(audio_int16.tobytes())

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"ChatTTS 音频生成成功: {output_path}")
                return True, "ChatTTS 音频生成成功", output_path
            else:
                return False, "ChatTTS 音频生成失败", None

        except Exception as e:
            logger.error(f"ChatTTS 生成失败: {e}")
            import traceback
            traceback.print_exc()
            # 回退到 edge-tts
            logger.info("回退到 edge-tts")
            return self._generate_with_edge_tts(dialogue_parts, speaker_voices, output_path)

    def _generate_with_edge_tts(
        self,
        dialogue_parts: List[Tuple[str, str]],
        speaker_voices: dict,
        output_path: str
    ) -> tuple[bool, str, Optional[str]]:
        """
        使用 edge-tts 生成多说话者对话
        """
        try:
            logger.info("使用 edge-tts 生成音频")

            # 为每个说话者生成音频片段
            audio_segments = []
            temp_files = []

            for speaker, text in dialogue_parts:
                voice = speaker_voices.get(speaker, "en-US-AriaNeural")

                # 创建临时文件
                temp_file = tempfile.mktemp(suffix=".mp3")
                temp_files.append(temp_file)

                # 生成音频
                success, msg, _ = self._edge_tts(text, temp_file, voice)
                if not success:
                    logger.error(f"生成音频失败: {msg}")
                    # 清理临时文件
                    for f in temp_files:
                        if os.path.exists(f):
                            os.remove(f)
                    return False, f"音频生成失败: {msg}", None

                audio_segments.append(temp_file)

            # 拼接所有音频片段
            success = self._concatenate_audio(audio_segments, output_path)

            # 清理临时文件
            for f in temp_files:
                if os.path.exists(f):
                    os.remove(f)

            if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"edge-tts 音频生成成功: {output_path}")
                return True, "edge-tts 音频生成成功", output_path
            else:
                return False, "音频拼接失败", None

        except Exception as e:
            logger.error(f"edge-tts 生成失败: {e}")
            import traceback
            traceback.print_exc()
            return False, f"edge-tts 生成失败: {str(e)}", None

    def _parse_dialogue(self, script: str) -> List[Tuple[str, str]]:
        """
        解析对话脚本

        Returns:
            List[Tuple[str, str]]: [(说话者, 台词), ...]
        """
        dialogue_parts = []
        lines = script.strip().split('\n')

        current_speaker = None
        current_text = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 匹配说话者标记：M:, W:, Man:, Woman:, Boy:, Girl:, A:, B: 等
            match = re.match(r'^([A-Z][a-z]*|M|W|A|B):\s*(.+)', line)
            if match:
                # 保存之前的对话
                if current_speaker and current_text:
                    dialogue_parts.append((current_speaker, ' '.join(current_text)))

                # 开始新的对话
                current_speaker = match.group(1)
                current_text = [match.group(2)]
            else:
                # 继续当前说话者的台词
                if current_speaker:
                    current_text.append(line)

        # 保存最后一段对话
        if current_speaker and current_text:
            dialogue_parts.append((current_speaker, ' '.join(current_text)))

        return dialogue_parts

    def _detect_context(self, script: str, dialogue_parts: List[Tuple[str, str]]) -> str:
        """
        检测对话语境

        Returns:
            str: 语境类型 (school, medical, shopping, family, restaurant, general)
        """
        script_lower = script.lower()

        # 检查各种语境的关键词
        for context, config in CONTEXT_PATTERNS.items():
            keyword_count = sum(1 for kw in config["keywords"] if kw in script_lower)
            # 学校语境只需要1个关键词即可匹配（更敏感）
            threshold = 1 if context == "school" else 2
            if keyword_count >= threshold:
                return context

        return "general"  # 默认通用语境

    def _get_scene_params(self, context: str) -> dict:
        """
        根据对话场景获取 ChatTTS 生成参数

        不同场景使用不同的温度、采样参数，以获得更符合场景的语音风格

        Args:
            context: 场景类型 (school, medical, shopping, family, restaurant, general)

        Returns:
            dict: 包含 temperature, top_P, top_K, repetition_penalty 等参数
        """
        # 默认参数（平衡模式）
        default_params = {
            'temperature': 0.3,      # 控制随机性，越低越稳定
            'top_P': 0.7,            # 核采样概率
            'top_K': 20,             # 保留 top-k 采样
            'repetition_penalty': 1.05  # 重复惩罚
        }

        # 场景特定参数
        scene_params = {
            'school': {
                'temperature': 0.25,      # 更稳定，适合教学
                'top_P': 0.65,            # 更保守的采样
                'top_K': 15,              # 更少的变化
                'repetition_penalty': 1.03
            },
            'medical': {
                'temperature': 0.3,       # 专业、稳重
                'top_P': 0.7,
                'top_K': 20,
                'repetition_penalty': 1.05
            },
            'shopping': {
                'temperature': 0.4,       # 更活泼，有变化
                'top_P': 0.8,             # 更多变化
                'top_K': 25,
                'repetition_penalty': 1.02
            },
            'family': {
                'temperature': 0.35,      # 温暖、自然
                'top_P': 0.75,
                'top_K': 20,
                'repetition_penalty': 1.0
            },
            'restaurant': {
                'temperature': 0.35,      # 活泼、有生气
                'top_P': 0.75,
                'top_K': 22,
                'repetition_penalty': 1.03
            },
            'general': default_params
        }

        return scene_params.get(context, default_params)

    def _analyze_characters_with_ai(
        self,
        dialogue_parts: List[Tuple[str, str]],
        context: str
    ) -> Optional[dict]:
        """
        使用 AI 分析对话中的角色特征

        Returns:
            Optional[dict]: {说话者: {age, gender, role, emotion}}
        """
        try:
            from zhipuai import ZhipuAI
            import os

            api_key = os.getenv("ZHIPU_API_KEY")
            if not api_key:
                logger.debug("ZHIPU_API_KEY 未设置，跳过 AI 分析")
                return None

            # 构建分析 prompt
            dialogue_text = "\n".join([f"{s}: {t}" for s, t in dialogue_parts])

            prompt = f"""分析以下英语对话中每个说话者的角色特征，返回 JSON 格式：

对话语境：{context}
对话内容：
{dialogue_text}

请分析每个说话者的以下特征：
1. age: 年龄组 (child/teenager/young_adult/adult/elderly)
2. gender: 性别 (male/female)
3. role: 角色 (student/teacher/patient/doctor/customer/clerk/parent/child等)
4. emotion: 情感基调 (casual/formal/friendly/professional/anxious等)

只返回 JSON，不要其他内容：
{{"M": {{"age": "young_adult", "gender": "male", "role": "student", "emotion": "casual"}}, "W": ...}}"""

            client = ZhipuAI(api_key=api_key)
            response = client.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )

            # 解析响应
            import json
            import re

            content = response.choices[0].message.content.strip()

            # 提取 JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # 清理
            content = re.sub(r',\s*}', '}', content)
            content = content.replace('\\n', ' ')

            profiles = json.loads(content)

            # 验证格式
            result = {}
            for speaker, profile in profiles.items():
                if isinstance(profile, dict) and "age" in profile and "gender" in profile:
                    result[speaker] = profile

            if result:
                logger.info(f"AI 分析结果: {result}")
                return result

        except ImportError:
            logger.debug("zhipuai 未安装")
        except Exception as e:
            logger.debug(f"AI 分析失败: {e}")

        return None

    def _assign_voices_by_profiles(self, speaker_profiles: dict) -> dict:
        """
        根据角色特征画像分配声音

        Args:
            speaker_profiles: {说话者: {age, gender, role, emotion}}

        Returns:
            dict: {说话者: edge-tts声音名称}
        """
        speaker_voices = {}

        # 角色特征到声音的映射规则
        def map_profile_to_voice(profile: dict) -> str:
            age = profile.get("age", "adult")
            gender = profile.get("gender", "male")
            role = profile.get("role", "")
            emotion = profile.get("emotion", "casual")

            # 根据年龄和性别选择基础声音
            if age in ["child", "teenager", "young_adult"]:
                if gender == "male":
                    base_voice = SPEAKER_VOICES["M_Young_Casual"]
                else:
                    base_voice = SPEAKER_VOICES["W_Young_Casual"]
            else:  # adult, elderly
                if gender == "male":
                    if emotion in ["professional", "formal"]:
                        base_voice = SPEAKER_VOICES["M_Adult_Professional"]
                    else:
                        base_voice = SPEAKER_VOICES["M_Adult_Warm"]
                else:
                    if emotion in ["professional", "formal"]:
                        base_voice = SPEAKER_VOICES["W_Adult_Professional"]
                    else:
                        base_voice = SPEAKER_VOICES["W_Adult_Friendly"]

            return base_voice

        for speaker, profile in speaker_profiles.items():
            speaker_voices[speaker] = map_profile_to_voice(profile)

        return speaker_voices

    def _assign_voices_by_context(
        self,
        dialogue_parts: List[Tuple[str, str]],
        context: str,
        custom_voice_map: Optional[dict] = None
    ) -> dict:
        """
        根据语境和说话者标记分配声音

        Args:
            dialogue_parts: 对话片段列表
            context: 语境类型
            custom_voice_map: 自定义声音映射

        Returns:
            dict: {说话者标记: edge-tts声音名称}
        """
        # 如果有自定义映射，直接使用
        if custom_voice_map:
            return custom_voice_map

        # 获取所有唯一的说话者
        speakers = list(set(speaker for speaker, _ in dialogue_parts))
        speaker_voices = {}

        if context == "school":
            # 学校语境：大多数听力对话是学生之间的对话
            # 即使提到老师，通常也是学生在谈论老师，而不是老师本人

            # 检查是否真的是老师在说话（给出指令、解释概念等）
            # 而不是学生在谈论他们的老师
            full_text = ' '.join(text for _, text in dialogue_parts).lower()

            # 老师说话的特征：直接解释、给出指令、使用祈使句、称呼"class"
            # 注意：需要区分学生谈论"课程"(English class)和老师称呼"同学们"(Good morning, class)
            teacher_speaking_patterns = [
                "good morning, class", "good afternoon, class", "good evening, class",
                "let me explain", "let's look at", "pay attention", "listen carefully",
                "you should", "you need to", "i want you to", "turn to", "open your",
                "today we'll", "today we are", "we'll learn", "we are going to"
            ]

            # 学生谈论老师的特征：提到 "Mr./Ms. + 姓名", "my teacher", "our professor"
            student_talking_about_teacher = [
                "mr. ", "ms. ", "mrs. ", "professor ", "my teacher", "our teacher",
                "my professor", "our professor"
            ]

            has_teacher_speaking = any(pattern in full_text for pattern in teacher_speaking_patterns)
            student_mentioning_teacher = any(pattern in full_text for pattern in student_talking_about_teacher)

            # 如果学生在谈论老师，说明两个说话者都是学生
            if student_mentioning_teacher and not has_teacher_speaking:
                # 两个都是学生
                for speaker in speakers:
                    if speaker in ["M", "Man", "Boy"]:
                        speaker_voices[speaker] = SPEAKER_VOICES["M_Young_Casual"]
                    elif speaker in ["W", "Woman", "Girl"]:
                        speaker_voices[speaker] = SPEAKER_VOICES["W_Young_Casual"]
                    else:
                        speaker_voices[speaker] = SPEAKER_VOICES["M_Young_Casual"]
            elif has_teacher_speaking:
                # 真的有老师在说话
                # 判断谁是老师（通常说指导性话语的是老师）
                for speaker, text in dialogue_parts:
                    text_lower = text.lower()
                    if any(pattern in text_lower for pattern in teacher_speaking_patterns):
                        # 这个说话者是老师
                        if speaker in ["M", "Man"]:
                            speaker_voices[speaker] = SPEAKER_VOICES["M_Adult_Professional"]
                        elif speaker in ["W", "Woman"]:
                            speaker_voices[speaker] = SPEAKER_VOICES["W_Adult_Professional"]
                        else:
                            speaker_voices[speaker] = SPEAKER_VOICES["M_Adult_Professional"]
                    elif speaker not in speaker_voices:
                        # 这个说话者是学生
                        if speaker in ["M", "Man", "Boy"]:
                            speaker_voices[speaker] = SPEAKER_VOICES["M_Young_Casual"]
                        elif speaker in ["W", "Woman", "Girl"]:
                            speaker_voices[speaker] = SPEAKER_VOICES["W_Young_Casual"]
                        else:
                            speaker_voices[speaker] = SPEAKER_VOICES["M_Young_Casual"]
            else:
                # 默认：同学之间的对话，都使用年轻声音
                for speaker in speakers:
                    if speaker in ["M", "Man", "Boy"]:
                        speaker_voices[speaker] = SPEAKER_VOICES["M_Young_Casual"]
                    elif speaker in ["W", "Woman", "Girl"]:
                        speaker_voices[speaker] = SPEAKER_VOICES["W_Young_Casual"]
                    else:
                        speaker_voices[speaker] = SPEAKER_VOICES["M_Young_Casual"]

        elif context == "medical":
            # 医疗语境：医生（成年）- 病人（成年）
            for speaker in speakers:
                if speaker in ["M", "Man"]:
                    speaker_voices[speaker] = SPEAKER_VOICES["M_Adult_Professional"]
                elif speaker in ["W", "Woman"]:
                    speaker_voices[speaker] = SPEAKER_VOICES["W_Adult_Friendly"]
                else:
                    speaker_voices[speaker] = SPEAKER_VOICES["M_Adult_Warm"]

        elif context == "shopping":
            # 购物语境：店员（成年）- 顾客（成年）
            for speaker in speakers:
                if speaker in ["M", "Man"]:
                    speaker_voices[speaker] = SPEAKER_VOICES["M_Adult_Friendly"]
                elif speaker in ["W", "Woman"]:
                    speaker_voices[speaker] = SPEAKER_VOICES["W_Adult_Friendly"]
                else:
                    speaker_voices[speaker] = SPEAKER_VOICES["W_Adult_Friendly"]

        elif context == "family":
            # 家庭语境：父母（成年）- 孩子（年轻）
            # 根据对话内容判断谁是父母
            for i, (speaker, text) in enumerate(dialogue_parts):
                text_lower = text.lower()
                if i == 0:
                    # 第一个说话者通常是父母
                    speaker_voices[speaker] = SPEAKER_VOICES["M_Adult_Warm"]
                else:
                    if any(kw in text_lower for kw in ["mom", "dad", "parent"]):
                        speaker_voices[speaker] = SPEAKER_VOICES["W_Young_Casual"]
                    else:
                        speaker_voices[speaker] = SPEAKER_VOICES["W_Adult_Friendly"]

        elif context == "restaurant":
            # 餐厅语境：服务员（成年）- 顾客（成年）
            for speaker in speakers:
                if speaker in ["M", "Man"]:
                    speaker_voices[speaker] = SPEAKER_VOICES["M_Adult_Friendly"]
                elif speaker in ["W", "Woman"]:
                    speaker_voices[speaker] = SPEAKER_VOICES["W_Adult_Friendly"]
                else:
                    speaker_voices[speaker] = SPEAKER_VOICES["W_Adult_Friendly"]

        else:  # general
            # 通用语境：默认成年声音
            for speaker in speakers:
                if speaker in ["M", "Man", "Boy"]:
                    speaker_voices[speaker] = SPEAKER_VOICES["M_Adult_Warm"]
                elif speaker in ["W", "Woman", "Girl"]:
                    speaker_voices[speaker] = SPEAKER_VOICES["W_Adult_Friendly"]
                else:
                    speaker_voices[speaker] = SPEAKER_VOICES["M_Adult_Warm"]

        return speaker_voices

    def _concatenate_audio(self, audio_files: List[str], output_path: str) -> bool:
        """
        拼接多个音频文件

        使用 ffmpeg 或 pydub 进行拼接
        """
        # 尝试使用 ffmpeg
        if self._concatenate_with_ffmpeg(audio_files, output_path):
            return True

        # 尝试使用 pydub
        if self._concatenate_with_pydub(audio_files, output_path):
            return True

        return False

    def _concatenate_with_ffmpeg(self, audio_files: List[str], output_path: str) -> bool:
        """使用 ffmpeg 拼接音频"""
        try:
            # 创建临时文件列表
            list_file = tempfile.mktemp(suffix=".txt")
            with open(list_file, 'w') as f:
                for audio_file in audio_files:
                    f.write(f"file '{os.path.abspath(audio_file)}'\n")

            # 使用 ffmpeg concat demuxer
            result = subprocess.run(
                [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', list_file,
                    '-c', 'copy',
                    '-y',  # 覆盖输出文件
                    output_path
                ],
                capture_output=True,
                timeout=30
            )

            # 清理列表文件
            if os.path.exists(list_file):
                os.remove(list_file)

            return result.returncode == 0 and os.path.exists(output_path)

        except Exception as e:
            logger.debug(f"ffmpeg 拼接失败: {e}")
            return False

    def _concatenate_with_pydub(self, audio_files: List[str], output_path: str) -> bool:
        """使用 pydub 拼接音频"""
        try:
            from pydub import AudioSegment

            # 加载并拼接音频
            combined = AudioSegment.empty()
            for audio_file in audio_files:
                audio = AudioSegment.from_mp3(audio_file)
                combined += audio

            # 导出
            combined.export(output_path, format="mp3")
            return True

        except ImportError:
            logger.debug("pydub 未安装")
            return False
        except Exception as e:
            logger.debug(f"pydub 拼接失败: {e}")
            return False

    def text_to_speech(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice: str = "en-US"
    ) -> tuple[bool, str, Optional[str]]:
        """
        文本转语音

        Args:
            text: 要转换的文本
            output_path: 输出文件路径
            voice: 声音类型

        Returns:
            tuple[bool, str, Optional[str]]: (是否成功, 消息, 文件路径)
        """
        if self.method == "chatts_lib":
            return self._chatts_lib(text, output_path)
        elif self.method == "edge_tts":
            return self._edge_tts(text, output_path, voice)
        elif self.method == "espeak":
            return self._espeak(text, output_path)
        else:
            return False, "未找到可用的 TTS 方法", None

    def _chatts_lib(
        self,
        text: str,
        output_path: Optional[str] = None
    ) -> tuple[bool, str, Optional[str]]:
        """使用 ChatTTS Python 库"""
        try:
            from ChatTTS import Chat
            import torch
            import wave
            import numpy as np
            import io

            chat = Chat()

            # 生成音频
            audio = chat.infer(
                text,
                voice='female',
                language='en'
            )

            # 保存为 WAV 文件
            if output_path is None:
                output_path = tempfile.mktemp(suffix=".wav")

            # 转换音频格式
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)

                # 归一化音频数据
                audio_array = audio[0]
                # 防止 clipping
                audio_array = np.clip(audio_array, -1.0, 1.0)
                audio_int16 = (audio_array * 32767).astype(np.int16)
                wf.writeframes(audio_int16.tobytes())

            # 写入文件
            with open(output_path, 'wb') as f:
                f.write(wav_buffer.getvalue())

            logger.info(f"ChatTTS 生成成功: {output_path}")
            return True, "音频生成成功", output_path

        except Exception as e:
            logger.error(f"ChatTTS 生成失败: {e}")
            return False, f"TTS 生成失败: {str(e)}", None

    def _edge_tts(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice: str = "en-US-AriaNeural"
    ) -> tuple[bool, str, Optional[str]]:
        """使用 edge-tts"""
        try:
            if output_path is None:
                output_path = tempfile.mktemp(suffix=".mp3")

            # 调用 edge-tts
            result = subprocess.run(
                [
                    "edge-tts",
                    "--voice", voice,
                    "--text", text,
                    "--write-media", output_path
                ],
                capture_output=True,
                timeout=60
            )

            # 检查结果
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"edge-tts 生成成功: {output_path}")
                return True, "音频生成成功", output_path
            else:
                error_msg = result.stderr.decode() if result.stderr else "未知错误"
                logger.error(f"edge-tts 失败: {error_msg}")
                return False, f"edge-tts 生成失败: {error_msg}", None

        except subprocess.TimeoutExpired:
            return False, "TTS 生成超时", None
        except Exception as e:
            logger.error(f"edge-tts 失败: {e}")
            return False, f"TTS 生成失败: {str(e)}", None

    def _espeak(
        self,
        text: str,
        output_path: Optional[str] = None
    ) -> tuple[bool, str, Optional[str]]:
        """使用 espeak (备用方案)"""
        try:
            if output_path is None:
                output_path = tempfile.mktemp(suffix=".wav")

            # 生成 WAV 文件
            result = subprocess.run(
                ["espeak", "-v", "en-us", "-w", output_path, text],
                capture_output=True,
                timeout=30
            )

            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"espeak 生成成功: {output_path}")
                return True, "音频生成成功", output_path
            else:
                return False, "espeak 生成失败", None

        except Exception as e:
            logger.error(f"espeak 失败: {e}")
            return False, f"TTS 生成失败: {str(e)}", None


# 单例实例
_tts_service = None

def get_local_tts() -> LocalTTSService:
    """获取本地 TTS 服务"""
    global _tts_service
    if _tts_service is None:
        _tts_service = LocalTTSService()
    return _tts_service
