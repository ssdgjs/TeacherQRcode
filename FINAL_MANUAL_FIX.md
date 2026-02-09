# 🎯 终极手动部署方案

## 问题诊断

经过多次尝试，自动化脚本都无法正常工作（expect脚本的SSH连接问题）。
**根本原因**：必须手动SSH执行，才能实时看到进度和错误信息。

---

## 🔧 完整手动步骤

### 第一步：SSH登录并检查现状

```bash
ssh ubuntu@182.254.159.223
密码: Yf19910201.
```

**登录后，执行以下诊断命令并告诉我结果**：

```bash
# 1. 检查目录是否存在
cd ~/eduqr-lite && pwd

# 2. 检查Git状态
git status
git log --oneline -3

# 3. 检查文件行数（新UI应该是1047行）
wc -l templates/index.html

# 4. 检查是否有新UI代码
head -30 templates/index.html | grep -i 'gradient\|toast\|shortcut'
```

---

### 第二步：根据诊断结果决定方案

#### 情况A：如果目录不存在或不是git仓库
```bash
cd ~
rm -rf eduqr-lite 2>/dev/null

# 克隆最新代码
git clone https://github.com/ssdgjs/TeacherQRcode.git eduqr-lite
cd eduqr-lite

# 验证文件（应该显示1047行）
wc -l templates/index.html

# 配置环境
cat > .env << 'EOF'
ADMIN_PASSWORD=Avic2026!
BASE_URL=http://182.254.159.223:8000
DATA_RETENTION_DAYS=30
EOF

# 删除旧镜像
sudo docker rmi eduqr-lite_web 2>/dev/null

# 完全重建（重要：--no-cache）
sudo docker-compose build --no-cache
sudo docker-compose up -d

# 验证
curl -s localhost:8000/ | wc -l  # 应该显示1047
```

#### 情况B：如果git仓库存在但文件是旧的
```bash
cd ~/eduqr-lite

# 拉取最新代码
git fetch origin
git reset --hard origin/main

# 验证文件
wc -l templates/index.html

# 完全重建
sudo docker-compose down
sudo docker rmi eduqr-lite_web
sudo docker-compose build --no-cache
sudo docker-compose up -d
```

#### 情况C：如果文件是新的但容器内是旧的
```bash
cd ~/eduqr-lite

# 检查容器内文件
sudo docker exec eduqr-lite_web_1 wc -l /app/templates/index.html

# 如果容器内文件行数不是1047，直接复制
sudo docker cp templates/index.html eduqr-lite_web_1:/app/templates/index.html

# 重启
sudo docker-compose restart
```

---

### 第三步：验证新UI

```bash
# 检查HTML行数（应该显示1047）
curl -s localhost:8000/ | wc -l

# 检查新特性
curl -s localhost:8000/ | grep -o "gradient-bg"
curl -s localhost:8000/ | grep -o "toast-container"
curl -s localhost:8000/ | grep -o "shortcuts-panel"
```

如果以上三个命令都有输出，说明新UI部署成功！

---

### 第四步：浏览器测试

1. 打开: http://182.254.159.223:8000
2. **强制刷新**清除浏览器缓存：
   - Mac: `Cmd + Shift + R`
   - Windows: `Ctrl + Shift + R`
3. 检查新UI特征：
   - ✨ 头部背景色循环变化
   - ⌨️ 右上角有?按钮
   - 按 `Ctrl+Enter` 测试快捷键

---

## 🐛 如果还是失败

如果手动执行也遇到问题，请告诉我具体的**错误信息**：

### 常见错误1：git clone失败
```
错误：Permission denied (publickey)
解决：使用 HTTPS 地址
git clone https://github.com/ssdgjs/TeacherQRcode.git eduqr-lite
```

### 常见错误2：Docker构建失败
```
错误：Get "https://registry-1.docker.io/v2/" timeout
解决：配置国内镜像源
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": ["https://mirror.ccs.tencentyun.com"]
}
EOF
sudo systemctl restart docker
```

### 常见错误3：端口被占用
```
错误：Bind for 0.0.0.0:8000 failed
解决：
sudo lsof -i :8000  # 查看占用端口的进程
sudo kill -9 [PID]  # 杀死进程
```

---

## 📞 需要帮助？

请执行第一步的诊断命令，然后把**所有输出**（包括任何错误信息）告诉我，我可以提供针对性的解决方案。

特别是这4个命令的输出：
1. `git log --oneline -3`
2. `wc -l templates/index.html`
3. `sudo docker ps`
4. `curl -s localhost:8000/ | wc -l`

这样我能准确知道问题在哪里！🔍
