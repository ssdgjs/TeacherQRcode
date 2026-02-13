"""
AI服务层 - 智谱AI GLM-4集成
"""
import json
import os
import re  # 新增：用于JSON修复
from typing import Dict, List, Any, Optional
from zhipuai import ZhipuAI
from prompts import PROMPT_TEMPLATES, SYSTEM_PROMPT


class ZhipuAIService:
    """智谱AI服务类"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化智谱AI服务

        Args:
            api_key: API密钥，如果不提供则从环境变量读取
        """
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY")
        if not self.api_key:
            raise ValueError("ZHIPU_API_KEY not found in environment variables")

        self.client = ZhipuAI(api_key=self.api_key)
        self.model = "glm-4-flash"  # 使用Flash模型（性价比高）

    def generate_questions(
        self,
        grade: str,
        topic: str,
        difficulty: str,
        question_types: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成英语作业题目

        Args:
            grade: 年级（如"初中二年级"）
            topic: 主题（如"现在完成时"）
            difficulty: 难度（easy/medium/hard）
            question_types: 题型列表，格式：[{"type": "choice", "count": 5}, ...]

        Returns:
            dict: 生成的作业数据
        """
        questions = []

        # 遍历每种题型
        for question_type in question_types:
            type_name = question_type.get("type")
            count = question_type.get("count", 1)

            # 获取对应的Prompt模板
            prompt_template = PROMPT_TEMPLATES.get(type_name)
            if not prompt_template:
                continue

            # 填充Prompt
            prompt = prompt_template.format(
                grade=grade,
                topic=topic,
                difficulty=difficulty,
                count=count
            )

            # 调用AI生成
            try:
                result = self._call_ai(prompt)
                questions.extend(result)
            except Exception as e:
                print(f"生成{type_name}题型失败: {e}")
                # 返回错误信息，不中断整个流程
                questions.append({
                    "type": type_name,
                    "error": f"生成失败: {str(e)}",
                    "questions": []
                })

        return {
            "grade": grade,
            "topic": topic,
            "difficulty": difficulty,
            "questions": questions
        }

    def _call_ai(self, prompt: str, max_retries: int = 3) -> List[Dict[str, Any]]:
        """
        调用智谱AI API

        Args:
            prompt: Prompt文本
            max_retries: 最大重试次数

        Returns:
            list: 生成的题目列表

        Raises:
            Exception: API调用失败
        """
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,  # 创造性和一致性的平衡
                    top_p=0.9,
                    max_tokens=2000
                )

                # 解析响应
                content = response.choices[0].message.content.strip()

                # 尝试提取JSON（处理可能的markdown代码块）
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                # 清理可能的格式问题
                # 移除可能的BOM标记
                if content.startswith('\ufeff'):
                    content = content[1:]

                # 尝试修复常见的JSON格式问题
                # 1. 移除注释
                lines = content.split('\n')
                cleaned_lines = []
                for line in lines:
                    # 跳过注释行（但不处理字符串内的//）
                    if '//' in line and not line.strip().startswith('"'):
                        # 检查是否在字符串中
                        in_string = False
                        quote_count = 0
                        for char in line:
                            if char in '"':
                                quote_count += 1
                                in_string = quote_count % 2 == 1
                        if not in_string and not line.strip().startswith('//'):
                            line = line.split('//')[0]
                    cleaned_lines.append(line)
                content = '\n'.join(cleaned_lines)

                # 尝试解析JSON
                try:
                    result = json.loads(content)
                except json.JSONDecodeError as e:
                    print(f"JSON解析失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                    print(f"原始响应: {content[:500]}...")

                    # 尝试修复JSON格式
                    if attempt < max_retries - 1:
                        # 移除可能的尾随逗号
                        content = re.sub(r',\s*}', '}', content)
                        # 修复未转义的换行符
                        content = content.replace('\\n', '\n').replace('\\"', '"')

                        try:
                            result = json.loads(content)
                            print(f"✅ JSON修复成功")
                        except:
                            continue
                    else:
                        raise Exception(f"AI生成的内容格式错误，无法解析为JSON: {str(e)}")

                # 根据不同的题型返回不同格式的数据
                if "questions" in result:
                    return result["questions"]
                elif "passages" in result:
                    return result["passages"]
                else:
                    return [result]

            except json.JSONDecodeError as e:
                print(f"JSON解析失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                print(f"原始响应: {content}")
                if attempt == max_retries - 1:
                    raise Exception(f"AI生成的内容格式错误，无法解析为JSON: {str(e)}")

            except Exception as e:
                print(f"AI调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"AI服务调用失败: {str(e)}")

        return []

    def test_connection(self) -> bool:
        """
        测试API连接

        Returns:
            bool: 连接是否成功
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            print(f"API连接测试失败: {e}")
            return False


# ==================== 单例模式 ====================
_ai_service: Optional[ZhipuAIService] = None


def get_ai_service() -> ZhipuAIService:
    """
    获取AI服务实例（单例模式）

    Returns:
        ZhipuAIService: AI服务实例
    """
    global _ai_service
    if _ai_service is None:
        _ai_service = ZhipuAIService()
    return _ai_service


# ==================== 辅助函数 ====================
def validate_generation_params(
    grade: str,
    topic: str,
    difficulty: str,
    question_types: List[Dict[str, Any]]
) -> tuple[bool, str]:
    """
    验证生成参数

    Args:
        grade: 年级
        topic: 主题
        difficulty: 难度
        question_types: 题型列表

    Returns:
        tuple[bool, str]: (是否有效, 错误信息)
    """
    # 验证年级
    valid_grades = [
        "小学三年级", "小学四年级", "小学五年级", "小学六年级",
        "初中一年级", "初中二年级", "初中三年级",
        "高中一年级", "高中二年级", "高中三年级"
    ]
    if grade not in valid_grades:
        return False, f"无效的年级，必须是: {', '.join(valid_grades)}"

    # 验证主题
    if not topic or len(topic.strip()) < 2:
        return False, "主题不能为空且至少2个字符"

    # 验证难度
    if difficulty not in ["easy", "medium", "hard"]:
        return False, "难度必须是: easy, medium, hard"

    # 验证题型
    if not question_types or len(question_types) == 0:
        return False, "至少选择一种题型"

    valid_types = set(PROMPT_TEMPLATES.keys())
    for qt in question_types:
        type_name = qt.get("type")
        if type_name not in valid_types:
            return False, f"无效的题型: {type_name}，必须是: {', '.join(valid_types)}"

        count = qt.get("count", 0)
        if not isinstance(count, int) or count < 1 or count > 20:
            return False, f"{type_name}的数量必须在1-20之间"

    return True, ""


# ==================== 音色推荐系统 ====================

class VoiceRecommendationService:
    """音色推荐服务"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化音色推荐服务

        Args:
            api_key: API密钥，如果不提供则从环境变量读取
        """
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY")
        if self.api_key:
            self.client = ZhipuAI(api_key=self.api_key)
        else:
            self.client = None

    # 预定义的音色配置
    VOICE_PRESETS = {
        "default": {
            "name": "默认配置",
            "description": "适合大多数场景的均衡配置",
            "voices": {
                "M": "en-US-ChristopherNeural",
                "W": "en-US-AriaNeural",
                "Man": "en-US-ChristopherNeural",
                "Woman": "en-US-AriaNeural",
                "Boy": "en-US-EricNeural",
                "Girl": "en-US-JennyNeural"
            }
        },
        "school": {
            "name": "校园场景",
            "description": "老师（成年）和学生（年轻）的对话",
            "voices": {
                "M": "en-US-BrianNeural",      # 男老师 - 深沉专业
                "W": "en-US-MichelleNeural",   # 女老师 - 专业温和
                "Man": "en-US-BrianNeural",
                "Woman": "en-US-MichelleNeural",
                "Boy": "en-US-EricNeural",     # 男学生 - 年轻活泼
                "Girl": "en-US-JennyNeural"    # 女学生 - 年轻甜美
            }
        },
        "medical": {
            "name": "医疗场景",
            "description": "医生和患者的专业对话",
            "voices": {
                "Doctor": "en-US-GuyNeural",      # 医生 - 专业稳重
                "Patient": "en-US-JennyNeural",   # 患者 - 自然亲切
                "M": "en-US-GuyNeural",
                "W": "en-US-JennyNeural"
            }
        },
        "shopping": {
            "name": "购物场景",
            "description": "店员和顾客的友好对话",
            "voices": {
                "Customer": "en-US-AriaNeural",   # 顾客 - 自然
                "Clerk": "en-US-JennyNeural",     # 店员 - 热情友好
                "M": "en-US-ChristopherNeural",
                "W": "en-US-AriaNeural"
            }
        },
        "family": {
            "name": "家庭场景",
            "description": "家庭成员间的温暖对话",
            "voices": {
                "Father": "en-US-ChristopherNeural",  # 父亲 - 温厚
                "Mother": "en-US-MichelleNeural",     # 母亲 - 温柔
                "Child": "en-US-JennyNeural",         # 孩子 - 活泼
                "M": "en-US-ChristopherNeural",
                "W": "en-US-MichelleNeural"
            }
        },
        "business": {
            "name": "商务场景",
            "description": "商务人士的专业对话",
            "voices": {
                "M": "en-US-BrianNeural",      # 专业商务男声
                "W": "en-US-MichelleNeural",   # 专业商务女声
                "Man": "en-US-BrianNeural",
                "Woman": "en-US-MichelleNeural"
            }
        }
    }

    def recommend_voice_config(
        self,
        dialogue_script: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        根据对话内容推荐音色配置

        Args:
            dialogue_script: 对话脚本文本
            context: 上下文场景（可选）

        Returns:
            dict: 推荐的音色配置
                {
                    "recommended_preset": str,  # 推荐的预设名称
                    "preset_name": str,         # 预设显示名称
                    "voice_map": dict,          # 说话者到音色的映射
                    "confidence": float,        # 推荐置信度 (0-1)
                    "reasoning": str            # 推荐理由
                }
        """
        # 分析对话内容，检测场景
        detected_scene = self._detect_scene(dialogue_script)

        # 如果提供了上下文，优先使用
        if context and context in self.VOICE_PRESETS:
            recommended_preset = context
        else:
            recommended_preset = detected_scene

        preset = self.VOICE_PRESETS[recommended_preset]

        # 解析对话中的说话者
        speakers = self._parse_speakers(dialogue_script)

        # 为每个说话者分配音色
        voice_map = {}
        for speaker in speakers:
            # 优先使用预设中该说话者的音色
            if speaker in preset["voices"]:
                voice_map[speaker] = preset["voices"][speaker]
            else:
                # 根据说话者标签推断性别和年龄
                voice_map[speaker] = self._infer_voice_for_speaker(speaker, preset)

        return {
            "recommended_preset": recommended_preset,
            "preset_name": preset["name"],
            "voice_map": voice_map,
            "confidence": self._calculate_confidence(dialogue_script, detected_scene),
            "reasoning": f"根据对话内容检测到'{preset['name']}'场景，推荐使用相应音色配置。"
        }

    def _detect_scene(self, dialogue_script: str) -> str:
        """
        检测对话场景

        Args:
            dialogue_script: 对话脚本

        Returns:
            str: 场景名称 (school, medical, shopping, family, business, default)
        """
        script_lower = dialogue_script.lower()

        # 场景关键词
        scene_keywords = {
            "school": ["teacher", "student", "class", "homework", "exam", "lesson", "school", "grade", "subject"],
            "medical": ["doctor", "patient", "medicine", "hospital", "pain", "symptom", "fever", "headache", "nurse"],
            "shopping": ["buy", "sell", "price", "shop", "store", "customer", "clerk", "cashier", "discount", "sale"],
            "family": ["father", "mother", "parent", "child", "son", "daughter", "family", "home", "house"],
            "business": ["meeting", "presentation", "client", "boss", "office", "company", "business", "project"]
        }

        # 统计每个场景的关键词出现次数
        scene_scores = {}
        for scene, keywords in scene_keywords.items():
            score = sum(1 for kw in keywords if kw in script_lower)
            scene_scores[scene] = score

        # 返回得分最高的场景
        if scene_scores:
            max_scene = max(scene_scores, key=scene_scores.get)
            if scene_scores[max_scene] > 0:
                return max_scene

        return "default"

    def _parse_speakers(self, dialogue_script: str) -> List[str]:
        """
        解析对话中的说话者

        Args:
            dialogue_script: 对话脚本

        Returns:
            list: 说话者列表
        """
        import re
        # 匹配对话行开头的说话者标签
        # 例如: "M:", "Woman:", "Doctor: Hello"
        pattern = r'^([A-Z][a-z]*|[A-Z]{1,2}|Man|Woman|Boy|Girl|Doctor|Patient|Teacher|Student|Customer|Clerk|Father|Mother|Child):\s'

        speakers = set()
        for line in dialogue_script.split('\n'):
            match = re.match(pattern, line)
            if match:
                speakers.add(match.group(1))

        return list(speakers) if speakers else ["M", "W"]

    def _infer_voice_for_speaker(self, speaker: str, preset: Dict[str, Any]) -> str:
        """
        为说话者推断合适的音色

        Args:
            speaker: 说话者标签
            preset: 预设配置

        Returns:
            str: 音色名称
        """
        speaker_lower = speaker.lower()

        # 根据标签推断性别
        if speaker_lower in ["m", "man", "boy", "father", "doctor", "teacher", "customer"]:
            # 男性/男角色
            if "boy" in speaker_lower or "child" in speaker_lower or "student" in speaker_lower:
                # 男孩/学生 - 使用年轻男声
                return preset["voices"].get("Boy", "en-US-EricNeural")
            else:
                # 成年男性 - 使用成年男声
                return preset["voices"].get("M", "en-US-ChristopherNeural")
        else:
            # 女性/女角色
            if "girl" in speaker_lower or "child" in speaker_lower or "student" in speaker_lower:
                # 女孩/学生 - 使用年轻女声
                return preset["voices"].get("Girl", "en-US-JennyNeural")
            else:
                # 成年女性 - 使用成年女声
                return preset["voices"].get("W", "en-US-AriaNeural")

    def _calculate_confidence(self, dialogue_script: str, detected_scene: str) -> float:
        """
        计算推荐置信度

        Args:
            dialogue_script: 对话脚本
            detected_scene: 检测到的场景

        Returns:
            float: 置信度 (0-1)
        """
        # 简单的置信度计算：基于对话长度和场景关键词
        script_length = len(dialogue_script)

        # 对话太短，置信度降低
        if script_length < 50:
            base_confidence = 0.5
        elif script_length < 200:
            base_confidence = 0.7
        else:
            base_confidence = 0.9

        # 如果检测到明确场景（非default），提高置信度
        if detected_scene != "default":
            base_confidence = min(base_confidence + 0.1, 1.0)

        return round(base_confidence, 2)

    def get_available_presets(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有可用的音色预设

        Returns:
            dict: 预设配置字典
        """
        return {
            key: {
                "name": value["name"],
                "description": value["description"],
                "voices": list(value["voices"].keys())
            }
            for key, value in self.VOICE_PRESETS.items()
        }

    def generate_custom_prompt(
        self,
        dialogue_script: str,
        current_voice_config: Dict[str, str],
        user_feedback: Optional[str] = None
    ) -> str:
        """
        生成用于重新抽卡的自定义提示词

        Args:
            dialogue_script: 对话脚本
            current_voice_config: 当前音色配置
            user_feedback: 用户反馈（可选）

        Returns:
            str: 生成的提示词
        """
        prompt_parts = [
            "请根据以下信息重新生成这道听力题：",
            f"\n对话内容：\n{dialogue_script}",
            f"\n当前音色配置：\n{json.dumps(current_voice_config, ensure_ascii=False, indent=2)}"
        ]

        if user_feedback:
            prompt_parts.append(f"\n用户反馈：{user_feedback}")

        prompt_parts.append("\n请保持相同的难度和题型，但根据反馈调整内容。")

        return "\n".join(prompt_parts)


# 便捷函数
def get_voice_recommender() -> VoiceRecommendationService:
    """获取音色推荐服务实例"""
    return VoiceRecommendationService()
