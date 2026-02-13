@echo off
chcp 65001 >nul
echo ==========================================
echo   EduQR Lite - 快速启动脚本 (Windows)
echo ==========================================
echo.

REM 检查 .env 文件
if not exist .env (
    echo ⚠️  未找到 .env 文件，从示例创建...
    copy .env.example .env
    echo ✅ 已创建 .env 文件
    echo.
    echo 📝 请先编辑 .env 文件，修改以下配置：
    echo    - ADMIN_PASSWORD: 设置管理暗号
    echo    - BASE_URL: 设置服务器地址（本地测试用 http://localhost:8000）
    echo.
    pause
)

REM 检查 Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未安装 Docker，请先安装 Docker Desktop
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未安装 Docker Compose，请先安装 Docker Compose
    pause
    exit /b 1
)

echo 🚀 启动服务...
echo.

REM 创建必要的目录
if not exist data mkdir data
if not exist uploads mkdir uploads

REM 启动服务
docker-compose up -d --build

echo.
echo ✅ 服务启动成功！
echo.
echo 📱 访问地址: http://localhost:8000
echo 📚 查看日志: docker-compose logs -f
echo 🛑 停止服务: docker-compose down
echo.
echo ==========================================
pause
