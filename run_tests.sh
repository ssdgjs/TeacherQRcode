#!/bin/bash
# 测试运行脚本

set -e

echo "=========================================="
echo "EduQR AI - 测试套件"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}警告: 虚拟环境不存在${NC}"
    echo "请先运行: python -m venv venv"
    exit 1
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate || source venv/bin/activate

# 安装测试依赖
echo ""
echo "安装测试依赖..."
pip install -q -r requirements-test.txt

# 运行测试
echo ""
echo "运行测试..."
echo "=========================================="

# 运行pytest并捕获结果
if pytest tests/ -v --tb=short --cov=. --cov-report=html --cov-report=term-missing --cov-ignore=tests/ "$@"; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo "✓ 所有测试通过！"
    echo "==========================================${NC}"
    echo ""
    echo "覆盖率报告已生成: htmlcov/index.html"
    echo "在浏览器中打开查看详情"
else
    echo ""
    echo -e "${RED}=========================================="
    echo "✗ 测试失败"
    echo "==========================================${NC}"
    echo ""
    echo "请查看上面的错误信息并修复"
    exit 1
fi
