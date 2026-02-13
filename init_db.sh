#!/bin/bash

# PostgreSQL 数据库初始化脚本
# 用于创建 EduQR AI 所需的数据库和用户

set -e

echo "================================"
echo "EduQR AI - 数据库初始化脚本"
echo "================================"

# 数据库配置
DB_NAME="eduqr"
DB_USER="eduqr"
DB_PASSWORD="eduqr_password"
DB_HOST="localhost"
DB_PORT="5432"

# 检查是否已安装 PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "❌ 未检测到 PostgreSQL，请先安装："
    echo "   Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib"
    echo "   macOS: brew install postgresql"
    exit 1
fi

echo "✅ 检测到 PostgreSQL 已安装"

# 询问是否继续
read -p "是否继续创建数据库 '$DB_NAME'? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 操作已取消"
    exit 1
fi

# 创建数据库和用户
echo "📝 创建数据库和用户..."

sudo -u postgres psql << EOF
-- 创建用户
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME') THEN
        CREATE DATABASE $DB_NAME;
        RAISE NOTICE '数据库 % 已创建', '$DB_NAME';
    ELSE
        RAISE NOTICE '数据库 % 已存在', '$DB_NAME';
    END IF;
END
\$\$;

-- 创建用户
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
        RAISE NOTICE '用户 % 已创建', '$DB_USER';
    ELSE
        RAISE NOTICE '用户 % 已存在', '$DB_USER';
    END IF;
END
\$\$;

-- 授权
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- 连接到数据库并授予 schema 权限
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
EOF

echo "✅ 数据库初始化完成！"
echo ""
echo "================================"
echo "数据库信息："
echo "  数据库名: $DB_NAME"
echo "  用户名: $DB_USER"
echo "  密码: $DB_PASSWORD"
echo "  主机: $DB_HOST"
echo "  端口: $DB_PORT"
echo ""
echo "连接字符串："
echo "  postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
echo "================================"
echo ""
echo "请将以下配置添加到 .env 文件："
echo "  DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
echo ""
echo "接下来运行："
echo "  1. 更新 .env 文件"
echo "  2. 运行数据库迁移: alembic upgrade head"
echo "  3. 启动应用: docker-compose up -d"
