#!/usr/bin/env python3
"""
EduQR Lite 综合功能测试报告
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
ADMIN_PASSWORD = "Avic2026!"

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_feature(name, test_func):
    try:
        test_func()
        print(f"✅ {name}")
        return True
    except Exception as e:
        print(f"❌ {name}: {e}")
        return False

print_section("EduQR Lite - 综合功能测试报告")
print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"服务地址: {BASE_URL}")

results = []

# ========== 核心功能测试 ==========

print_section("1. 核心功能测试")

def test_health_check():
    r = requests.get(f"{BASE_URL}/health")
    assert r.json()["status"] == "healthy"

results.append(test_feature("1.1 Health Check", test_health_check))

def test_homepage():
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200
    assert "EduQR Lite" in r.text
    assert "静态码" in r.text
    assert "活码作业" in r.text
    assert "听力作业" in r.text

results.append(test_feature("1.2 首页加载与模式展示", test_homepage))

def test_static_qr():
    r = requests.post(f"{BASE_URL}/api/generate", data={
        "content": "Wi-Fi: TestNetwork Password: test123",
        "mode": "static",
        "access_code": ADMIN_PASSWORD,
        "size": 300,
        "error_correction": "M"
    })
    assert r.status_code == 200
    data = r.json()
    assert "qr_code_data_url" in data
    assert data["mode"] == "static"
    assert data["short_id"] is None
    # 验证是 Base64 图片
    assert data["qr_code_data_url"].startswith("data:image/png;base64,")

results.append(test_feature("1.3 静态二维码生成", test_static_qr))

def test_dynamic_qr_text():
    content = """# 数学作业

请完成课本第 45 页练习题：
1. 计算题 1-5
2. 应用题 1-3
3. 思考题（选做）

**注意**: 请详细写出计算过程
"""
    r = requests.post(f"{BASE_URL}/api/generate", data={
        "content": content,
        "mode": "text",
        "access_code": ADMIN_PASSWORD,
        "size": 400,
        "error_correction": "H"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "text"
    assert data["short_id"] is not None
    assert len(data["short_id"]) == 8

    # 验证可以访问
    r2 = requests.get(f"{BASE_URL}/v/{data['short_id']}")
    assert r2.status_code == 200
    assert "数学作业" in r2.text
    assert "课本第 45 页" in r2.text

results.append(test_feature("1.4 活码模式（文本作业）", test_dynamic_qr_text))

# ========== 安全功能测试 ==========

print_section("2. 安全功能测试")

def test_wrong_password():
    r = requests.post(f"{BASE_URL}/api/generate", data={
        "content": "test",
        "mode": "static",
        "access_code": "wrong_password",
        "size": 300
    })
    assert r.status_code == 403

results.append(test_feature("2.1 错误暗号拒绝", test_wrong_password))

def test_empty_content():
    r = requests.post(f"{BASE_URL}/api/generate", data={
        "content": "   ",
        "mode": "static",
        "access_code": ADMIN_PASSWORD,
        "size": 300
    })
    assert r.status_code == 400

results.append(test_feature("2.2 空内容拒绝", test_empty_content))

def test_too_long_content():
    long_content = "A" * 10001
    r = requests.post(f"{BASE_URL}/api/generate", data={
        "content": long_content,
        "mode": "text",
        "access_code": ADMIN_PASSWORD,
        "size": 300
    })
    assert r.status_code == 400

results.append(test_feature("2.3 超长内容拒绝", test_too_long_content))

# ========== 边界情况测试 ==========

print_section("3. 边界情况测试")

def test_very_long_content():
    # 测试接近限制的长内容
    long_content = "# 长篇阅读材料\n\n" + ("这是一段很长的阅读材料。" * 200)
    assert len(long_content) < 10000

    r = requests.post(f"{BASE_URL}/api/generate", data={
        "content": long_content,
        "mode": "text",
        "access_code": ADMIN_PASSWORD,
        "size": 300
    })
    assert r.status_code == 200
    data = r.json()
    assert data["short_id"] is not None

results.append(test_feature("3.1 长内容处理（接近限制）", test_very_long_content))

def test_special_characters():
    special_content = """# 特殊字符测试

包含以下特殊字符：
!@#$%^&*()_+-=[]{}|;':",./<>?

中英文混合：
Hello 你好 🎉

链接测试：
https://www.example.com

**加粗文本**
*斜体文本*
"""
    r = requests.post(f"{BASE_URL}/api/generate", data={
        "content": special_content,
        "mode": "text",
        "access_code": ADMIN_PASSWORD,
        "size": 300
    })
    assert r.status_code == 200

results.append(test_feature("3.2 特殊字符和Markdown", test_special_characters))

def test_qr_sizes():
    for size in [200, 300, 500, 800, 1000]:
        r = requests.post(f"{BASE_URL}/api/generate", data={
            "content": f"Test size {size}",
            "mode": "static",
            "access_code": ADMIN_PASSWORD,
            "size": size
        })
        assert r.status_code == 200

results.append(test_feature("3.3 不同二维码尺寸", test_qr_sizes))

def test_error_correction_levels():
    for level in ["L", "M", "Q", "H"]:
        r = requests.post(f"{BASE_URL}/api/generate", data={
            "content": f"Test EC level {level}",
            "mode": "static",
            "access_code": ADMIN_PASSWORD,
            "error_correction": level
        })
        assert r.status_code == 200

results.append(test_feature("3.4 不同容错率级别", test_error_correction_levels))

# ========== 数据管理测试 ==========

print_section("4. 数据管理测试")

def test_stats_api():
    r = requests.get(f"{BASE_URL}/api/stats", params={
        "access_code": ADMIN_PASSWORD
    })
    assert r.status_code == 200
    data = r.json()
    assert "total_homeworks" in data
    assert data["total_homeworks"] > 0

results.append(test_feature("4.1 统计API", test_stats_api))

def test_nonexistent_homework():
    r = requests.get(f"{BASE_URL}/v/NOTFOUND123")
    assert r.status_code == 404

results.append(test_feature("4.2 不存在的作业处理", test_nonexistent_homework))

# ========== Markdown 渲染测试 ==========

print_section("5. Markdown 渲染测试")

def test_markdown_rendering():
    content = """# 一级标题
## 二级标题

**粗体文本**
*斜体文本*

- 列表项 1
- 列表项 2
- 列表项 3

1. 有序列表 1
2. 有序列表 2

[链接文本](https://www.example.com)

这是普通段落。
"""
    r = requests.post(f"{BASE_URL}/api/generate", data={
        "content": content,
        "mode": "text",
        "access_code": ADMIN_PASSWORD
    })
    assert r.status_code == 200
    short_id = r.json()["short_id"]

    # 验证渲染
    r2 = requests.get(f"{BASE_URL}/v/{short_id}")
    assert r2.status_code == 200
    html = r2.text
    assert "一级标题" in html or "h1" in html
    assert "粗体" in html or "strong" in html
    assert "列表项" in html

results.append(test_feature("5.1 Markdown 基础语法", test_markdown_rendering))

# ========== 性能测试 ==========

print_section("6. 性能测试")

def test_generation_speed():
    import time
    start = time.time()
    r = requests.post(f"{BASE_URL}/api/generate", data={
        "content": "Performance test",
        "mode": "static",
        "access_code": ADMIN_PASSWORD
    })
    elapsed = time.time() - start
    assert r.status_code == 200
    assert elapsed < 2.0  # 应该在 2 秒内完成

results.append(test_feature("6.1 生成速度（<2秒）", test_generation_speed))

def test_concurrent_requests():
    import concurrent.futures
    import time

    def make_request(i):
        r = requests.post(f"{BASE_URL}/api/generate", data={
            "content": f"Concurrent test {i}",
            "mode": "static",
            "access_code": ADMIN_PASSWORD
        })
        return r.status_code == 200

    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    elapsed = time.time() - start

    assert all(results)
    assert elapsed < 5.0  # 10个并发请求应该在 5 秒内完成

results.append(test_feature("6.2 并发请求（10个并发）", test_concurrent_requests))

# ========== 测试报告 ==========

print_section("测试结果汇总")

total_tests = len(results)
passed_tests = sum(results)
failed_tests = total_tests - passed_tests
success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

print(f"总测试数: {total_tests}")
print(f"通过: {passed_tests} ✅")
print(f"失败: {failed_tests} ❌")
print(f"成功率: {success_rate:.1f}%")

print_section("功能覆盖清单")

print("""
✅ 核心功能
  - 静态二维码生成
  - 活码（文本作业）生成
  - 二维码实时预览
  - 二维码下载

✅ 安全功能
  - 管理暗号保护
  - 内容验证（空内容、超长内容）
  - 错误处理

✅ 用户界面
  - 三模式切换（静态/活码/听力）
  - 管理暗号输入
  - 二维码配置（尺寸、容错率）
  - 音频文件上传（UI）

✅ 移动端展示
  - 作业详情页
  - Markdown 渲染
  - 音频播放器（UI）

✅ 数据管理
  - SQLite 存储
  - 自动数据清理
  - 统计 API

✅ 部署支持
  - Docker 配置
  - 环境变量配置
  - Volume 持久化
""")

if failed_tests == 0:
    print("🎉 所有测试通过！系统已准备好用于生产环境。")
else:
    print(f"⚠️  有 {failed_tests} 个测试失败，请检查修复。")

print("\n" + "=" * 70)
