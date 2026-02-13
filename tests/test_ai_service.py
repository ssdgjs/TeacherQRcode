"""
AI服务模块单元测试
"""
import pytest
import json
from unittest.mock import Mock, patch

from ai_service import ZhipuAIService, get_ai_service, validate_generation_params
from prompts import SYSTEM_PROMPT, PROMPT_TEMPLATES


@pytest.mark.unit
@pytest.mark.ai
class TestAIServiceInit:
    """AI服务初始化测试"""

    @patch.dict('os.environ', {'ZHIPU_API_KEY': 'test_api_key'})
    def test_get_ai_service(self):
        """测试获取AI服务实例"""
        service = get_ai_service()

        assert service is not None
        assert isinstance(service, ZhipuAIService)

    def test_ai_service_singleton(self):
        """测试AI服务单例模式"""
        with patch.dict('os.environ', {'ZHIPU_API_KEY': 'test_api_key'}):
            service1 = get_ai_service()
            service2 = get_ai_service()

            assert service1 is service2


@pytest.mark.unit
@pytest.mark.ai
class TestPromptGeneration:
    """提示词生成测试"""

    def test_multiple_choice_prompt_template(self):
        """测试选择题提示词模板"""
        template = PROMPT_TEMPLATES.get("choice")

        assert template is not None
        assert "{grade}" in template
        assert "{topic}" in template
        assert "{difficulty}" in template
        assert "{count}" in template

    def test_fill_in_blank_prompt_template(self):
        """测试填空题提示词模板"""
        template = PROMPT_TEMPLATES.get("fill_blank")

        assert template is not None
        assert "{count}" in template

    def test_all_question_types_have_templates(self):
        """测试所有题型都有提示词模板"""
        expected_types = ["choice", "fill_blank", "true_false", "reading", "listening", "essay"]

        for q_type in expected_types:
            assert q_type in PROMPT_TEMPLATES
            assert PROMPT_TEMPLATES[q_type] is not None


@pytest.mark.unit
@pytest.mark.ai
class TestParameterValidation:
    """参数验证测试"""

    def test_valid_generation_params(self):
        """测试有效的生成参数"""
        grade = "初中二年级"
        topic = "现在完成时"
        difficulty = "medium"
        question_types = [
            {"type": "choice", "count": 5},
            {"type": "fill_blank", "count": 5}
        ]

        is_valid, error = validate_generation_params(
            grade, topic, difficulty, question_types
        )

        assert is_valid is True
        assert error == ""

    def test_invalid_grade(self):
        """测试无效的年级"""
        is_valid, error = validate_generation_params(
            "", "现在完成时", "medium", []
        )

        assert is_valid is False
        assert "年级" in error

    def test_invalid_topic(self):
        """测试无效的主题"""
        is_valid, error = validate_generation_params(
            "初中二年级", "", "medium", []
        )

        assert is_valid is False
        assert "主题" in error

    def test_invalid_difficulty(self):
        """测试无效的难度"""
        is_valid, error = validate_generation_params(
            "初中二年级", "现在完成时", "invalid", []
        )

        assert is_valid is False
        assert "难度" in error

    def test_invalid_question_types_empty(self):
        """测试空的题型列表"""
        is_valid, error = validate_generation_params(
            "初中二年级", "现在完成时", "medium", []
        )

        assert is_valid is False
        assert "至少选择一种题型" in error

    def test_invalid_question_type(self):
        """测试无效的题型"""
        is_valid, error = validate_generation_params(
            "初中二年级", "现在完成时", "medium",
            [{"type": "invalid_type", "count": 5}]
        )

        assert is_valid is False

    def test_invalid_count_too_large(self):
        """测试题目数量过大"""
        is_valid, error = validate_generation_params(
            "初中二年级", "现在完成时", "medium",
            [{"type": "choice", "count": 100}]
        )

        assert is_valid is False
        assert "数量" in error  # 错误消息应该包含"数量"


@pytest.mark.unit
@pytest.mark.ai
class TestAICall:
    """AI调用测试（使用mock）"""

    @patch('ai_service.ZhipuAI')
    def test_call_ai_success(self, mock_zhipuai_class):
        """测试AI调用成功"""
        # Mock响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''```json
{
  "questions": [
    {
      "question": "Test question?",
      "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"],
      "answer": "A",
      "explanation": "Test"
    }
  ]
}
```'''

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_zhipuai_class.return_value = mock_client

        with patch.dict('os.environ', {'ZHIPU_API_KEY': 'test_key'}):
            service = ZhipuAIService()
            service.client = mock_client

            result = service._call_ai("Test prompt")

            assert result is not None
            assert isinstance(result, list)
            assert len(result) > 0
            assert "question" in result[0]

    @patch('ai_service.ZhipuAI')
    def test_call_ai_retries_on_failure(self, mock_zhipuai_class):
        """测试AI调用失败时重试"""
        # 前两次失败，第三次成功
        mock_response_success = Mock()
        mock_response_success.choices = [Mock()]
        mock_response_success.choices[0].message.content = '{"questions": []}'

        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = [
            Exception("API Error 1"),
            Exception("API Error 2"),
            mock_response_success
        ]
        mock_zhipuai_class.return_value = mock_client

        with patch.dict('os.environ', {'ZHIPU_API_KEY': 'test_key'}):
            service = ZhipuAIService()
            service.client = mock_client

            result = service._call_ai("Test prompt", max_retries=3)

            assert result is not None
            assert mock_client.chat.completions.create.call_count == 3

    @patch('ai_service.ZhipuAI')
    def test_call_ai_all_retries_fail(self, mock_zhipuai_class):
        """测试所有重试都失败"""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_zhipuai_class.return_value = mock_client

        with patch.dict('os.environ', {'ZHIPU_API_KEY': 'test_key'}):
            service = ZhipuAIService()
            service.client = mock_client

            with pytest.raises(Exception):
                service._call_ai("Test prompt", max_retries=3)


@pytest.mark.unit
@pytest.mark.ai
class TestQuestionGeneration:
    """题目生成测试"""

    @patch('ai_service.ZhipuAI')
    def test_generate_questions_single_type(self, mock_zhipuai_class):
        """测试生成单一题型"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''```json
{
  "questions": [
    {
      "question": "Test?",
      "options": ["A", "B", "C", "D"],
      "answer": "A",
      "explanation": "Test"
    }
  ]
}
```'''

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_zhipuai_class.return_value = mock_client

        with patch.dict('os.environ', {'ZHIPU_API_KEY': 'test_key'}):
            service = ZhipuAIService()
            service.client = mock_client

            result = service.generate_questions(
                grade="初中二年级",
                topic="现在完成时",
                difficulty="medium",
                question_types=[{"type": "choice", "count": 1}]
            )

            assert result["grade"] == "初中二年级"
            assert result["topic"] == "现在完成时"
            assert result["difficulty"] == "medium"
            assert "questions" in result
            assert len(result["questions"]) > 0

    @patch('ai_service.ZhipuAI')
    def test_generate_questions_multiple_types(self, mock_zhipuai_class):
        """测试生成多种题型"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''```json
{
  "questions": [
    {
      "type": "choice",
      "question": "Test?",
      "options": ["A", "B", "C", "D"],
      "answer": "A",
      "explanation": "Test"
    }
  ]
}
```'''

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_zhipuai_class.return_value = mock_client

        with patch.dict('os.environ', {'ZHIPU_API_KEY': 'test_key'}):
            service = ZhipuAIService()
            service.client = mock_client

            result = service.generate_questions(
                grade="初中二年级",
                topic="现在完成时",
                difficulty="medium",
                question_types=[
                    {"type": "choice", "count": 1},
                    {"type": "fill_blank", "count": 1}
                ]
            )

            # 应该调用AI两次
            assert mock_client.chat.completions.create.call_count == 2
            assert len(result["questions"]) == 2


@pytest.mark.unit
@pytest.mark.ai
class TestResponseParsing:
    """响应解析测试"""

    def test_parse_json_from_markdown(self):
        """测试从markdown中解析JSON"""
        markdown_response = '''Here's the response:

```json
{
  "questions": [
    {"question": "Test"}
  ]
}
```

That's it!'''

        # 提取JSON
        if "```json" in markdown_response:
            content = markdown_response.split("```json")[1].split("```")[0].strip()
        else:
            content = markdown_response

        result = json.loads(content)

        assert "questions" in result
        assert isinstance(result["questions"], list)

    def test_parse_plain_json(self):
        """测试解析纯JSON"""
        plain_json = '{"questions": [{"question": "Test"}]}'

        result = json.loads(plain_json)

        assert "questions" in result


@pytest.mark.unit
@pytest.mark.ai
class TestSystemPrompt:
    """系统提示词测试"""

    def test_system_prompt_exists(self):
        """测试系统提示词存在"""
        assert SYSTEM_PROMPT is not None
        assert len(SYSTEM_PROMPT) > 0

    def test_system_prompt_content(self):
        """测试系统提示词内容"""
        assert "英语教师" in SYSTEM_PROMPT
        assert "JSON" in SYSTEM_PROMPT
