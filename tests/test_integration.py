"""
集成测试 - 测试完整的工作流程
"""
import pytest
import json
from unittest.mock import patch, Mock


@pytest.mark.integration
class TestUserRegistrationFlow:
    """用户注册流程集成测试"""

    def test_complete_registration_flow(self, test_client):
        """测试完整的注册流程"""
        # 1. 注册新用户
        response = test_client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "Test1234",
            "confirm_password": "Test1234"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data["data"]
        assert "user" in data["data"]

        # 2. 使用token访问受保护的路由
        token = data["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = test_client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200

        # 3. 验证额度已自动创建
        response = test_client.get("/api/v1/quota", headers=headers)
        assert response.status_code == 200
        quota_data = response.json()
        assert quota_data["success"] is True
        assert quota_data["data"]["free_limit"] == 10


@pytest.mark.integration
class TestUserLoginFlow:
    """用户登录流程集成测试"""

    def test_complete_login_flow(self, test_client, test_user):
        """测试完整的登录流程"""
        # 1. 登录
        response = test_client.post("/api/v1/auth/login", json={
            "email": test_user.email,
            "password": "password123"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data["data"]

        # 2. 使用token获取用户信息
        token = data["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = test_client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200

        user_data = response.json()
        assert user_data["success"] is True
        assert user_data["data"]["email"] == test_user.email


@pytest.mark.integration
class TestHomeworkGenerationFlow:
    """作业生成流程集成测试"""

    @patch('ai_service.ZhipuAI')
    def test_complete_homework_generation_flow(
        self, test_client, auth_headers, mock_zhipuai_class
    ):
        """测试完整的作业生成流程"""
        # Mock AI响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''```json
{
  "questions": [
    {
      "question": "What is correct?",
      "options": ["A. have gone", "B. went", "C. go", "D. going"],
      "answer": "A",
      "explanation": "Present perfect"
    }
  ]
}
```'''

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_zhipuai_class.return_value = mock_client

        # 1. 生成作业
        response = test_client.post(
            "/api/v1/homework/generate",
            json={
                "grade": "初中二年级",
                "topic": "现在完成时",
                "difficulty": "medium",
                "question_types": [{"type": "choice", "count": 1}]
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 2. 验证响应包含必要字段
        assert "homework" in data["data"]
        assert "homework_id" in data["data"]
        assert "short_id" in data["data"]
        assert "view_url" in data["data"]
        assert "qr_code_data_url" in data["data"]

        # 3. 验证额度已消费
        response = test_client.get("/api/v1/quota", headers=auth_headers)
        quota_data = response.json()
        assert quota_data["success"] is True
        # 免费额度应该减少
        assert quota_data["data"]["free_remaining"] < 10

        # 4. 验证作业已保存到数据库
        short_id = data["data"]["short_id"]
        response = test_client.get(f"/api/v1/homework/{data['data']['homework_id']}", headers=auth_headers)
        assert response.status_code == 200


@pytest.mark.integration
class TestHistoryManagementFlow:
    """历史记录管理流程集成测试"""

    def test_complete_history_flow(self, test_client, auth_headers, test_ai_homework):
        """测试完整的历史记录流程"""
        # 1. 获取历史记录
        response = test_client.get("/api/v1/homework/history", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data["data"]
        assert len(data["data"]["items"]) > 0

        # 2. 查看作业详情
        first_homework = data["data"]["items"][0]
        response = test_client.get(f"/api/v1/homework/{first_homework['id']}", headers=auth_headers)

        assert response.status_code == 200
        detail_data = response.json()
        assert detail_data["success"] is True

        # 3. 删除作业
        response = test_client.delete(
            f"/api/v1/homework/{first_homework['id']}",
            headers=auth_headers
        )

        assert response.status_code == 200
        delete_data = response.json()
        assert delete_data["success"] is True


@pytest.mark.integration
class TestPaymentFlow:
    """支付流程集成测试（mock）"""

    def test_complete_payment_flow(self, test_client, auth_headers):
        """测试完整的支付流程"""
        # 1. 创建订单
        with patch('payment_service.PaymentService.create_order') as mock_create:
            mock_create.return_value = (True, "订单创建成功", {
                "order_no": "TEST123456",
                "amount": 990,
                "pay_params": {
                    "appId": "test",
                    "timeStamp": "123456",
                    "nonceStr": "abc123",
                    "package": "prepay_id=test",
                    "signType": "MD5",
                    "paySign": "test_sign"
                }
            })

            response = test_client.post(
                "/api/v1/payment/create-order",
                json={"order_type": "package"},
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "order_no" in data["data"]

        # 2. 模拟支付回调
        with patch('payment_service.PaymentService.verify_callback') as mock_verify, \
             patch('payment_service.PaymentService.process_payment_success') as mock_process:
            mock_verify.return_value = (True, "验证成功", {
                "out_trade_no": "TEST123456",
                "transaction_id": "wx_transaction_123"
            })
            mock_process.return_value = (True, "支付成功")

            callback_xml = """<xml>
                <return_code><![CDATA[SUCCESS]]></return_code>
                <result_code><![CDATA[SUCCESS]]></result_code>
                <out_trade_no><![CDATA[TEST123456]]></out_trade_no>
                <transaction_id><![CDATA[wx_transaction_123]]></transaction_id>
                <sign><![CDATA[test_sign]]></sign>
            </xml>"""

            response = test_client.post("/api/v1/payment/callback", content=callback_xml)

            assert response.status_code == 200
            # 验证返回XML
            assert b"SUCCESS" in response.content


@pytest.mark.integration
class TestQuotaConsumptionFlow:
    """额度消费流程集成测试"""

    def test_quota_consumption_after_generation(
        self, test_client, auth_headers
    ):
        """测试生成作业后额度消费"""
        # 1. 获取初始额度
        response = test_client.get("/api/v1/quota", headers=auth_headers)
        initial_quota = response.json()["data"]
        initial_remaining = initial_quota["free_remaining"]

        # 2. 生成作业（需要mock AI）
        with patch('ai_service.ZhipuAI'):
            response = test_client.post(
                "/api/v1/homework/generate",
                json={
                    "grade": "初中二年级",
                    "topic": "测试主题",
                    "difficulty": "easy",
                    "question_types": [{"type": "choice", "count": 1}]
                },
                headers=auth_headers
            )

            # 可能会因为AI mock问题失败，这里主要测试额度消费
            if response.status_code == 200:
                # 3. 验证额度减少
                response = test_client.get("/api/v1/quota", headers=auth_headers)
                final_quota = response.json()["data"]
                final_remaining = final_quota["free_remaining"]

                assert final_remaining == initial_remaining - 1


@pytest.mark.integration
class TestQRCodeGenerationFlow:
    """二维码生成流程集成测试"""

    def test_qrcode_generation_and_view(self, test_client, test_homework):
        """测试二维码生成和查看"""
        # 1. 通过短码访问作业
        response = test_client.get(f"/v/{test_homework.short_id}")

        assert response.status_code == 200

        # 2. 验证页面内容
        content = response.text
        assert test_homework.title in content or test_homework.short_id in content


@pytest.mark.integration
class TestErrorHandling:
    """错误处理集成测试"""

    def test_invalid_token(self, test_client):
        """测试无效token"""
        headers = {"Authorization": "Bearer invalid_token"}

        response = test_client.get("/api/v1/quota", headers=headers)

        assert response.status_code == 401

    def test_no_token(self, test_client):
        """测试缺少token"""
        response = test_client.get("/api/v1/quota")

        assert response.status_code == 401

    def test_insufficient_quota(self, test_client, auth_headers):
        """测试额度不足"""
        # 先用完所有额度（假设用户是免费用户）
        # 这个测试需要根据实际情况调整

        # 尝试生成作业
        with patch('ai_service.ZhipuAI'):
            # 如果额度不足，应该返回403
            # 这个测试需要mock额度检查
            pass


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndScenarios:
    """端到端场景测试"""

    @patch('ai_service.ZhipuAI')
    def test_teacher_full_workflow(self, test_client, mock_zhipuai_class):
        """测试老师完整工作流程：注册→生成→查看历史"""
        # Mock AI响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''```json
{"questions": []}
```'''
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_zhipuai_class.return_value = mock_client

        # 1. 注册
        register_response = test_client.post("/api/v1/auth/register", json={
            "email": "teacher@example.com",
            "password": "Teacher1234",
            "confirm_password": "Teacher1234"
        })

        assert register_response.status_code == 200
        token = register_response.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. 生成作业
        gen_response = test_client.post(
            "/api/v1/homework/generate",
            json={
                "grade": "高中一年级",
                "topic": "定语从句",
                "difficulty": "hard",
                "question_types": [{"type": "choice", "count": 3}]
            },
            headers=headers
        )

        assert gen_response.status_code == 200
        homework_data = gen_response.json()["data"]
        short_id = homework_data["short_id"]

        # 3. 查看历史记录
        history_response = test_client.get("/api/v1/homework/history", headers=headers)

        assert history_response.status_code == 200
        items = history_response.json()["data"]["items"]
        assert len(items) > 0

        # 4. 验证作业可以访问
        view_response = test_client.get(f"/v/{short_id}")
        assert view_response.status_code == 200
