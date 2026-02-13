"""
支付服务 - 微信支付集成
支持：JSAPI支付、订单管理、回调验证
"""
import os
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from sqlmodel import Session, select
from models import Order, User, Quota

import httpx


# ==================== 配置 ====================
class PaymentConfig:
    """支付配置"""

    # 微信支付商户配置
    APP_ID: str = os.getenv("WECHAT_APP_ID", "your_app_id")
    MCH_ID: str = os.getenv("WECHAT_MCH_ID", "your_mch_id")
    API_KEY: str = os.getenv("WECHAT_API_KEY", "your_api_key")
    API_V3_KEY: str = os.getenv("WECHAT_API_V3_KEY", "your_api_v3_key")
    NOTIFY_URL: str = os.getenv("WECHAT_NOTIFY_URL", "https://your-domain.com/api/v1/payment/callback")

    # 价格配置（单位：分）
    PACKAGE_PRICE: int = 990  # 100次 = ¥9.90
    MONTHLY_PRICE: int = 990  # 月卡 = ¥9.90

    # 商品配置
    PACKAGE_COUNT: int = 100  # 次数包包含的次数
    MONTHLY_DAYS: int = 30  # 月卡有效天数

    # API配置
    PAYMENT_API_URL: str = "https://api.mch.weixin.qq.com/pay/unifiedorder"
    ORDER_QUERY_API: str = "https://api.mch.weixin.qq.com/pay/orderquery"
    TIMEOUT: int = 30  # 请求超时时间（秒）


# ==================== 工具函数 ====================
def generate_order_no() -> str:
    """生成订单号"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = uuid.uuid4().hex[:8].upper()
    return f"ORD{timestamp}{random_str}"


def md5_sign(params: Dict[str, str], api_key: str) -> str:
    """
    生成MD5签名（微信支付V2版本）

    Args:
        params: 签名参数
        api_key: 商户密钥

    Returns:
        签名字符串（大写）
    """
    # 1. 参数排序
    sorted_params = sorted(params.items())

    # 2. 拼接字符串
    sign_str = "&".join([f"{k}={v}" for k, v in sorted_params if v])

    # 3. 添加商户密钥
    sign_str += f"&key={api_key}"

    # 4. MD5加密并转大写
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()


def verify_sign(params: Dict[str, str], api_key: str) -> bool:
    """
    验证签名

    Args:
        params: 包含sign的参数
        api_key: 商户密钥

    Returns:
        是否验证成功
    """
    received_sign = params.pop("sign", "")
    calculated_sign = md5_sign(params, api_key)
    return received_sign == calculated_sign


# ==================== 支付服务类 ====================
class PaymentService:
    """支付服务"""

    def __init__(self):
        self.config = PaymentConfig()
        self.client = httpx.Client(timeout=self.config.TIMEOUT)

    def create_order(
        self,
        session: Session,
        user_id: int,
        order_type: str,
        client_ip: str
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        创建支付订单

        Args:
            session: 数据库会话
            user_id: 用户ID
            order_type: 订单类型（package/subscription）
            client_ip: 客户端IP

        Returns:
            (是否成功, 消息, 订单数据)
        """
        # 1. 验证订单类型
        if order_type not in ["package", "subscription"]:
            return False, "无效的订单类型", None

        # 2. 计算金额
        if order_type == "package":
            amount = self.config.PACKAGE_PRICE
            body = f"EduQR - {self.config.PACKAGE_COUNT}次生成包"
        else:
            amount = self.config.MONTHLY_PRICE
            body = "EduQR - 月度会员（30天）"

        # 3. 生成订单号
        order_no = generate_order_no()

        # 4. 创建订单记录
        try:
            order = Order(
                user_id=user_id,
                order_no=order_no,
                type=order_type,
                amount=amount,
                status="pending"
            )
            session.add(order)
            session.commit()
            session.refresh(order)
        except Exception as e:
            return False, f"创建订单失败: {str(e)}", None

        # 5. 调用微信支付统一下单API
        try:
            # 构建支付参数
            params = {
                "appid": self.config.APP_ID,
                "mch_id": self.config.MCH_ID,
                "nonce_str": uuid.uuid4().hex[:32].upper(),
                "body": body,
                "out_trade_no": order_no,
                "total_fee": amount,
                "spbill_create_ip": client_ip,
                "notify_url": self.config.NOTIFY_URL,
                "trade_type": "JSAPI",
                "openid": "user_openid"  # TODO: 从用户信息获取
            }

            # 生成签名
            params["sign"] = md5_sign(params, self.config.API_KEY)

            # 发送请求（XML格式）
            xml_data = self.dict_to_xml(params)
            response = self.client.post(
                self.config.PAYMENT_API_URL,
                content=xml_data,
                headers={"Content-Type": "application/xml"}
            )

            # 解析响应
            result = self.xml_to_dict(response.text)

            if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
                # 返回支付参数
                prepay_id = result.get("prepay_id")

                # 生成前端支付参数
                pay_params = self.generate_jsapi_params(prepay_id, order_no)

                return True, "订单创建成功", {
                    "order_no": order_no,
                    "amount": amount,
                    "pay_params": pay_params
                }
            else:
                error_msg = result.get("return_msg", result.get("err_code_des", "未知错误"))
                return False, f"支付下单失败: {error_msg}", None

        except Exception as e:
            return False, f"调用微信支付API失败: {str(e)}", None

    def generate_jsapi_params(self, prepay_id: str, order_no: str) -> Dict[str, str]:
        """
        生成JSAPI支付参数

        Args:
            prepay_id: 预支付交易会话标识
            order_no: 订单号

        Returns:
            JSAPI支付参数
        """
        timestamp = str(int(datetime.now().timestamp()))
        nonce_str = uuid.uuid4().hex[:32].upper()
        package = f"prepay_id={prepay_id}"

        params = {
            "appId": self.config.APP_ID,
            "timeStamp": timestamp,
            "nonceStr": nonce_str,
            "package": package,
            "signType": "MD5"
        }

        # 生成签名
        params["paySign"] = md5_sign(params, self.config.API_KEY)

        return params

    def verify_callback(self, xml_data: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        验证支付回调

        Args:
            xml_data: XML格式的回调数据

        Returns:
            (是否验证成功, 消息, 解析后的数据)
        """
        # 解析XML
        try:
            data = self.xml_to_dict(xml_data)
        except Exception as e:
            return False, f"解析回调数据失败: {str(e)}", None

        # 验证签名
        if not verify_sign(data.copy(), self.config.API_KEY):
            return False, "签名验证失败", None

        # 检查返回状态
        if data.get("return_code") != "SUCCESS":
            return False, data.get("return_msg", "支付失败"), None

        if data.get("result_code") != "SUCCESS":
            return False, data.get("err_code_des", "支付失败"), None

        return True, "验证成功", data

    def process_payment_success(
        self,
        session: Session,
        order_no: str,
        transaction_id: str
    ) -> Tuple[bool, str]:
        """
        处理支付成功

        Args:
            session: 数据库会话
            order_no: 订单号
            transaction_id: 微信支付交易号

        Returns:
            (是否成功, 消息)
        """
        # 1. 查找订单
        order = session.exec(
            select(Order).where(Order.order_no == order_no)
        ).first()

        if not order:
            return False, "订单不存在"

        # 2. 检查订单状态
        if order.status == "paid":
            return True, "订单已处理"

        # 3. 更新订单状态
        order.status = "paid"
        order.wechat_prepay_id = transaction_id
        order.paid_at = datetime.now()

        # 4. 增加用户额度
        try:
            quota = session.exec(
                select(Quota).where(Quota.user_id == order.user_id)
            ).first()

            if not quota:
                return False, "用户额度记录不存在"

            if order.type == "package":
                # 次数包：增加购买次数
                quota.purchased_count += PaymentConfig.PACKAGE_COUNT
            else:
                # 订阅：设置订阅到期时间
                if quota.subscription_expires_at and quota.subscription_expires_at > datetime.now():
                    # 已有订阅，在原基础上延长
                    quota.subscription_expires_at += timedelta(days=PaymentConfig.MONTHLY_DAYS)
                else:
                    # 新订阅或已过期，从今天开始计算
                    quota.subscription_expires_at = datetime.now() + timedelta(days=PaymentConfig.MONTHLY_DAYS)

            quota.updated_at = datetime.now()
            session.commit()

            return True, "支付成功，额度已到账"

        except Exception as e:
            session.rollback()
            return False, f"更新额度失败: {str(e)}"

    def query_order(self, order_no: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        查询订单状态

        Args:
            order_no: 订单号

        Returns:
            (是否成功, 消息, 订单数据)
        """
        # 构建查询参数
        params = {
            "appid": self.config.APP_ID,
            "mch_id": self.config.MCH_ID,
            "out_trade_no": order_no,
            "nonce_str": uuid.uuid4().hex[:32].upper()
        }

        # 生成签名
        params["sign"] = md5_sign(params, self.config.API_KEY)

        # 发送请求
        try:
            xml_data = self.dict_to_xml(params)
            response = self.client.post(
                self.config.ORDER_QUERY_API,
                content=xml_data,
                headers={"Content-Type": "application/xml"}
            )

            result = self.xml_to_dict(response.text)

            if result.get("return_code") == "SUCCESS":
                return True, "查询成功", result
            else:
                return False, result.get("return_msg", "查询失败"), None

        except Exception as e:
            return False, f"查询订单失败: {str(e)}", None

    def get_user_orders(self, session: Session, user_id: int, limit: int = 20) -> list:
        """
        获取用户订单列表

        Args:
            session: 数据库会话
            user_id: 用户ID
            limit: 返回数量

        Returns:
            订单列表
        """
        orders = session.exec(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        ).all()

        return [
            {
                "id": order.id,
                "order_no": order.order_no,
                "type": order.type,
                "amount": order.amount,
                "status": order.status,
                "created_at": order.created_at.isoformat(),
                "paid_at": order.paid_at.isoformat() if order.paid_at else None
            }
            for order in orders
        ]

    @staticmethod
    def dict_to_xml(data: Dict[str, str]) -> str:
        """字典转XML"""
        xml = "<xml>"
        for k, v in data.items():
            xml += f"<{k}>{v}</{k}>"
        xml += "</xml>"
        return xml

    @staticmethod
    def xml_to_dict(xml_data: str) -> Dict[str, str]:
        """XML转字典"""
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_data)
            return {child.tag: child.text for child in root}
        except Exception as e:
            raise ValueError(f"解析XML失败: {str(e)}")

    def test_connection(self) -> bool:
        """
        测试支付服务连接

        Returns:
            是否连接成功
        """
        # 简化版测试：检查配置是否完整
        return all([
            self.config.APP_ID != "your_app_id",
            self.config.MCH_ID != "your_mch_id",
            self.config.API_KEY != "your_api_key"
        ])


# ==================== 全局实例 ====================
_payment_service: Optional[PaymentService] = None


def get_payment_service() -> PaymentService:
    """获取支付服务实例"""
    global _payment_service
    if _payment_service is None:
        _payment_service = PaymentService()
    return _payment_service
