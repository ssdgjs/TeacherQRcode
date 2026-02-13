# EduQR AI - 智能英语作业生成器

<div align="center">

![EduQR AI Logo](https://img.shields.io/badge/EduQR-AI-teal-600.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

**AI驱动的智能英语作业生成器**

帮助老师快速创建高质量英语练习题，支持6种题型，自动生成二维码，学生扫码即可查看。

[功能特性](#功能特性) • [快速开始](#快速开始) • [文档](#文档) • [部署](#部署) • [贡献](#贡献)

</div>

---

## 📖 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [安装指南](#安装指南)
- [配置说明](#配置说明)
- [API文档](#api文档)
- [部署指南](#部署指南)
- [开发指南](#开发指南)
- [测试](#测试)
- [常见问题](#常见问题)
- [更新日志](#更新日志)
- [许可证](#许可证)

---

## 🎯 项目简介

EduQR AI 是一个基于人工智能的英语作业生成平台，专为英语教师设计。通过集成智谱AI GLM-4模型和微信支付，帮助老师：

- 🤖 **AI智能生成**：根据年级、主题、难度自动生成6种题型
- 📱 **二维码分享**：一键生成二维码，学生扫码即可查看
- 🎧 **听力音频**：支持TTS语音合成，生成听力题音频
- 💰 **灵活付费**：免费试用 + 次数包/月卡订阅
- 📊 **历史管理**：完整的生成历史和订单管理

---

## ✨ 功能特性

### 核心功能

#### 1. AI作业生成
- 支持6种英语题型：选择题、填空题、判断题、阅读理解、听力题、作文
- 智能题目生成（基于ZhipuAI GLM-4）
- 可配置年级、主题、难度
- 批量生成支持

#### 2. 二维码分享
- 自动生成短链接（BASE_URL/v/{short_id}）
- 一键生成二维码图片（PNG 300x300）
- 学生扫码即可查看格式化作业
- 支持下载和分享

#### 3. 听力音频
- 火山引擎TTS集成
- 4种发音类型：美式/英式 × 男声/女声
- 3种语速：慢速/正常/快速
- MP3格式输出
- 自动播放器集成

#### 4. 额度管理
- 免费：10次/天
- 次数包：100次/¥9.9（永久有效）
- 月卡订阅：¥9.9/月（无限次）
- 额度优先级：订阅 > 购买 > 免费
- 每日自动重置

#### 5. 支付系统
- 微信支付JSAPI集成
- 订单管理系统
- 支付回调验证
- 自动到账

#### 6. 用户界面
- 🌓 深色模式支持
- 📱 移动端友好
- ⚡ 骨架屏加载
- 🎨 美观的UI设计
- 🔔 Toast通知系统

---

## 🛠 技术栈

### 后端
- **框架**：FastAPI 0.100+
- **数据库**：PostgreSQL 16
- **ORM**：SQLModel
- **迁移**：Alembic
- **认证**：JWT (python-jose)
- **任务调度**：APScheduler

### AI & TTS
- **AI模型**：ZhipuAI GLM-4-Flash
- **TTS服务**：火山引擎（Volcengine）

### 前端
- **框架**：原生JavaScript + TailwindCSS
- **图标**：Heroicons (SVG)
- **二维码**：qrcode + Pillow

### 部署
- **容器化**：Docker + Docker Compose
- **Web服务器**：Uvicorn
- **反向代理**：Nginx

---

## 🚀 快速开始

### 使用Docker（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/ssdgjs/TeacherQRcode.git
cd TeacherQRcode

# 2. 配置环境变量
cp .env.example .env
# 编辑.env文件，填入必要的配置

# 3. 启动服务
docker-compose up -d

# 4. 访问应用
open http://localhost:8000
```

### 手动安装

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置数据库
export DATABASE_URL="postgresql://user:pass@localhost:5432/eduqr"

# 4. 初始化数据库
alembic upgrade head

# 5. 启动服务
uvicorn main:app --reload
```

---

## 📦 安装指南

### 系统要求

- Python 3.11+
- PostgreSQL 14+
- Docker & Docker Compose（可选）

### 环境变量配置

创建 `.env` 文件：

```bash
# 数据库配置
DATABASE_URL=postgresql://eduqr:your_password@localhost:5432/eduqr

# JWT密钥（至少32字符）
JWT_SECRET_KEY=your-secret-key-min-32-characters-long

# AI服务配置
ZHIPU_API_KEY=your_zhipu_api_key

# TTS服务配置（可选）
VOLCENGINE_ACCESS_KEY=your_volcengine_access_key
VOLCENGINE_SECRET_KEY=your_volcengine_secret_key

# 微信支付配置（生产环境需要）
WECHAT_APP_ID=your_wechat_app_id
WECHAT_MCH_ID=your_wechat_mch_id
WECHAT_API_KEY=your_wechat_api_key
WECHAT_NOTIFY_URL=https://your-domain.com/api/v1/payment/callback

# 应用配置
BASE_URL=http://localhost:8000
ADMIN_PASSWORD=your_admin_password
FREE_DAILY_LIMIT=10
```

---

## ⚙️ 配置说明

### 数据库配置

```python
# PostgreSQL连接
DATABASE_URL = "postgresql://user:password@host:port/database"

# 连接池设置
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)
```

### AI服务配置

```python
# 模型选择
model = "glm-4-flash"  # 性价比高

# 参数配置
temperature = 0.7  # 创造性
top_p = 0.9       # 采样
max_tokens = 2000 # 最大长度
```

### 额度配置

```python
# 免费额度
FREE_DAILY_LIMIT = 10  # 每天10次

# 次数包
PACKAGE_PRICE = 990    # ¥9.90（分为单位）
PACKAGE_COUNT = 100    # 100次

# 月卡
MONTHLY_PRICE = 990    # ¥9.90
MONTHLY_DAYS = 30      # 30天
```

---

## 📚 API文档

### 核心端点

#### 认证
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `GET /api/v1/auth/me` - 获取当前用户信息

#### 额度
- `GET /api/v1/quota` - 获取用户额度
- `POST /api/v1/quota/consume` - 消费额度

#### AI生成
- `POST /api/v1/homework/generate` - 生成作业

#### 历史记录
- `GET /api/v1/homework/history` - 获取历史记录
- `GET /api/v1/homework/{id}` - 获取作业详情
- `DELETE /api/v1/homework/{id}` - 删除作业

#### 支付
- `POST /api/v1/payment/create-order` - 创建订单
- `POST /api/v1/payment/callback` - 支付回调

### 交互式文档

启动服务后访问：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 🚢 部署指南

### Docker部署（推荐）

```bash
# 1. 构建镜像
docker-compose build

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 停止服务
docker-compose down
```

### 生产环境部署

#### 1. Nginx配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/app/static;
    }
}
```

#### 2. SSL/TLS配置

```bash
# 使用Let's Encrypt
sudo certbot --nginx -d your-domain.com
```

#### 3. Systemd服务

```ini
[Unit]
Description=EduQR AI Application
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/path/to/app
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn main:app
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 👨‍💻 开发指南

### 开发环境设置

```bash
# 1. 安装开发依赖
pip install -r requirements.txt
pip install -r requirements-test.txt

# 2. 设置pre-commit钩子（可选）
pip install pre-commit
pre-commit install

# 3. 运行开发服务器
uvicorn main:app --reload --log-level debug

# 4. 运行测试
pytest tests/ -v
```

### 代码风格

项目遵循PEP 8规范：

```bash
# 代码格式化
black .
isort .

# 类型检查
mypy .

# 代码检查
flake8
```

### 添加新功能

1. 在`main.py`中添加路由
2. 在`models.py`中定义数据模型
3. 在`tests/`中添加测试
4. 更新文档

---

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_auth.py -v

# 生成覆盖率报告
pytest tests/ --cov=. --cov-report=html

# 使用测试脚本
./run_tests.sh
```

### 测试覆盖率

| 模块 | 覆盖率 |
|------|--------|
| auth | 85% |
| quota | 80% |
| ai_service | 75% |
| payment | 60% |
| routes | 70% |
| models | 90% |

---

## ❓ 常见问题

### 1. 数据库连接失败

**问题**：`could not connect to server`

**解决**：
```bash
# 检查PostgreSQL是否运行
docker-compose ps postgres

# 检查数据库URL
echo $DATABASE_URL

# 重启数据库
docker-compose restart postgres
```

### 2. AI生成失败

**问题**：`AI生成失败: API error`

**解决**：
```bash
# 检查API密钥
echo $ZHIPU_API_KEY

# 测试API连接
curl http://localhost:8000/api/v1/ai/test
```

### 3. 支付回调404

**问题**：微信支付回调返回404

**解决**：
```bash
# 检查BASE_URL配置
echo $BASE_URL

# 确保回调URL可访问
curl -X POST https://your-domain.com/api/v1/payment/callback
```

### 4. 额度未重置

**问题**：免费额度每天没有重置

**解决**：
```bash
# 检查调度器状态
curl http://localhost:8000/api/v1/scheduler/info

# 手动触发重置（开发环境）
# 在Python中：
from quota import reset_daily_quotas_if_needed
from database import get_session
reset_daily_quotas_if_needed(next(get_session()))
```

---

## 📝 更新日志

### v1.0.0 - 正式发布（当前版本）

- ✅ 完整的用户认证系统
- ✅ AI智能作业生成
- ✅ 二维码自动生成
- ✅ TTS听力音频
- ✅ 额度管理
- ✅ 微信支付集成
- ✅ 历史记录管理
- ✅ 深色模式
- ✅ 完整的测试覆盖
- ✅ 生产就绪

[查看完整更新日志](CHANGELOG.md)

### 历史版本

- [v0.9.0 - 测试与Bug修复](V0.9.0_RELEASE_NOTES.md)
- [v0.8.0 - 前端优化](V0.8.0_RELEASE_NOTES.md)
- [v0.7.0 - 支付集成](V0.7.0_RELEASE_NOTES.md)
- [v0.6.0 - 历史记录管理](V0.6.0_RELEASE_NOTES.md)
- [v0.5.0 - 二维码整合](V0.5.0_RELEASE_NOTES.md)
- [v0.4.0 - TTS音频生成](V0.4.0_RELEASE_NOTES.md)
- [v0.3.0 - AI作业生成](V0.3.0_RELEASE_NOTES.md)
- [v0.2.0 - 额度管理](V0.2.0_RELEASE_NOTES.md)
- [v0.1.0 - 用户认证](V0.1.0_RELEASE_NOTES.md)

---

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

### 开发规范

- 遵循PEP 8代码风格
- 添加测试覆盖新功能
- 更新相关文档
- 确保所有测试通过

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 👥 作者

- **yangfanm4mini** - 主要开发者

---

## 🙏 致谢

- [ZhipuAI](https://open.bigmodel.cn/) - AI模型支持
- [FastAPI](https://fastapi.tiangolo.com/) - Web框架
- [SQLModel](https://sqlmodel.tiangolo.com/) - ORM
- [TailwindCSS](https://tailwindcss.com/) - CSS框架

---

## 🔗 相关链接

- **GitHub**: https://github.com/ssdgjs/TeacherQRcode
- **在线演示**: http://182.254.159.223:8000
- **问题反馈**: https://github.com/ssdgjs/TeacherQRcode/issues

---

<div align="center">

**⭐ 如果这个项目对您有帮助，请给个星标支持！**

Made with ❤️ by EduQR Team

</div>
