"""
AI服务层 - 智谱AI GLM-4集成
"""
import json
import os
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

                # 解析JSON
                result = json.loads(content)

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
    valid_types = set(PROMPT_TEMPLATES.keys())
    for qt in question_types:
        type_name = qt.get("type")
        if type_name not in valid_types:
            return False, f"无效的题型: {type_name}，必须是: {', '.join(valid_types)}"

        count = qt.get("count", 0)
        if not isinstance(count, int) or count < 1 or count > 20:
            return False, f"{type_name}的数量必须在1-20之间"

    return True, ""
