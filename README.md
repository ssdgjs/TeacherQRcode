# EduQR Lite - 简易作业二维码生成器

极简、无广告、私有化部署的作业二维码生成工具，专为教育场景设计。

## 功能特性

### 三种模式
- **📝 静态码**：短文本直接编码，无需网络即可扫描
- **📄 活码作业**：长文本托管，生成短链接二维码
- **🎧 听力作业**：支持音频文件上传 + 题目文本

### 核心功能
- ✅ 无广告、无注册、无隐私收集
- ✅ 支持长篇作业内容（10,000 字符）
- ✅ 移动端友好的作业展示页
- ✅ 支持 MP3/WAV/M4A 音频格式
- ✅ 基础 Markdown 渲染（加粗、列表、链接）
- ✅ 管理暗号保护，防止滥用
- ✅ 自动数据清理（可配置保留天数）
- ✅ Docker 一键部署

## 快速开始

### 方式一：Docker Compose（推荐）

1. **克隆或下载项目**
```bash
cd DownloadQRcode
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，修改 ADMIN_PASSWORD 和 BASE_URL
```

3. **启动服务**
```bash
docker-compose up -d --build
```

4. **访问应用**
打开浏览器访问 `http://localhost:8000`

### 方式二：本地运行

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **配置环境变量**
```bash
export ADMIN_PASSWORD="your-password"
export BASE_URL="http://localhost:8000"
```

3. **运行应用**
```bash
python main.py
```

## 使用指南

### 创建二维码

1. 打开网站，输入**管理暗号**
2. 选择模式（静态码/活码作业/听力作业）
3. 输入作业内容
4. （听力作业）上传音频文件
5. 调整二维码设置（容错率、尺寸）
6. 点击"生成二维码"
7. 下载 PNG 图片

### 学生查看作业

学生用手机扫描二维码后，会自动跳转到移动端友好的作业展示页：
- 查看文本内容
- 播放听力音频（如有）
- 点击链接访问相关资源

## 配置说明

### 环境变量

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `ADMIN_PASSWORD` | ✅ | - | 管理员暗号 |
| `BASE_URL` | ✅ | `http://localhost:8000` | 服务器地址 |
| `DATA_RETENTION_DAYS` | ❌ | `30` | 数据保留天数 |
| `MAX_CONTENT_LENGTH` | ❌ | `10000` | 最大字符数 |
| `MAX_UPLOAD_SIZE_MB` | ❌ | `20` | 音频文件最大大小 |
| `ALLOWED_AUDIO_EXTENSIONS` | ❌ | `mp3,wav,m4a,ogg` | 允许的音频格式 |
| `QR_CODE_SIZE` | ❌ | `300` | 默认二维码尺寸 |
| `QR_ERROR_CORRECTION` | ❌ | `M` | 默认容错率 |

### Docker Volume 挂载

```yaml
volumes:
  - ./data:/app/data              # SQLite 数据库
  - ./uploads:/app/static/uploads # 音频文件
```

定期备份这两个目录即可完整备份数据。

## 技术架构

```
前端：HTML5 + TailwindCSS (CDN)
后端：Python FastAPI
数据库：SQLite
二维码：qrcode Python 库
部署：Docker + Docker Compose
```

### 文件结构

```
/app
├── main.py              # FastAPI 应用入口
├── models.py            # SQLite 数据模型
├── utils.py             # 工具函数
├── templates/
│   ├── index.html       # 创建器页面
│   └── view.html        # 作业展示页
├── static/
│   └── uploads/         # 音频文件存储
├── data/                # SQLite 数据库
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 部署到腾讯云 Lighthouse

### 1. 准备服务器

```bash
# 安装 Docker 和 Docker Compose
curl -fsSL https://get.docker.com | sh
sudo apt install docker-compose
```

### 2. 上传项目

```bash
# 在本地打包项目
tar czf eduqr-lite.tar.gz DownloadQRcode/

# 上传到服务器
scp eduqr-lite.tar.gz root@your-server-ip:/root/

# 在服务器上解压
ssh root@your-server-ip
cd /root
tar xzf eduqr-lite.tar.gz
cd DownloadQRcode
```

### 3. 配置并启动

```bash
# 配置环境变量
cp .env.example .env
nano .env
# 修改 ADMIN_PASSWORD 和 BASE_URL

# 启动服务
docker-compose up -d --build
```

### 4. 配置防火墙

```bash
# 开放 80 端口（HTTP）
sudo ufw allow 80/tcp

# 如果使用域名，配置 DNS 解析到服务器 IP
```

## 数据管理

### 备份数据

```bash
# 备份数据库和音频文件
tar czf backup-$(date +%Y%m%d).tar.gz data/ uploads/

# 恢复
tar xzf backup-20260208.tar.gz
```

### 查看统计

访问 `/api/stats?access_code=你的暗号` 查看作业总数和存储占用。

## 常见问题

### Q: 二维码扫描后显示"作业不存在"？
A: 检查 `.env` 中的 `BASE_URL` 是否正确设置为服务器地址（本地测试用 `localhost`，生产环境用公网 IP 或域名）。

### Q: 音频文件上传失败？
A: 检查文件大小是否超过 20MB，格式是否为 MP3/WAV/M4A/OGG。

### Q: 如何删除某个作业？
A: 目前需要手动操作数据库：
```bash
docker exec -it eduqr-lite-web-1 sqlite3 /app/data/data.db
DELETE FROM homework_items WHERE short_id = 'abc123';
```

### Q: 如何延长数据保留时间？
A: 修改 `.env` 中的 `DATA_RETENTION_DAYS`，然后重启容器：
```bash
docker-compose restart
```

## 安全建议

1. **设置强密码**：`ADMIN_PASSWORD` 至少 12 位，包含大小写字母、数字和特殊字符
2. **定期备份数据**：每周备份 `data/` 和 `uploads/` 目录
3. **监控存储空间**：音频文件会占用磁盘空间，建议设置合理的保留天数
4. **使用 HTTPS**：生产环境建议配置 Nginx 反向代理 + SSL 证书

## 许可证

MIT License

## 更新日志

### v1.1 (2026-02-08)
- ✨ 新增听力作业模式
- ✨ 支持音频文件上传（MP3/WAV/M4A）
- ✨ 移动端音频播放器
- 🐛 修复若干问题

### v1.0 (2026-02-08)
- 🎉 初始版本
- ✅ 静态码/活码双模式
- ✅ 基础 Markdown 渲染
- ✅ Docker 部署支持
