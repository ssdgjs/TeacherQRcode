#!/usr/bin/env python3
"""
EduQR Lite 功能测试脚本
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"
ADMIN_PASSWORD = "Avic2026!"

print("=" * 60)
print("🧪 EduQR Lite 功能测试")
print("=" * 60)

# Test 1: Health Check
print("\n[TEST 1] Health Check")
try:
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✅ Health check passed")
except Exception as e:
    print(f"❌ Health check failed: {e}")
    exit(1)

# Test 2: Homepage
print("\n[TEST 2] Homepage Loading")
try:
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200
    assert "EduQR Lite" in response.text
    print("✅ Homepage loaded successfully")
except Exception as e:
    print(f"❌ Homepage failed: {e}")
    exit(1)

# Test 3: Static QR Code Generation
print("\n[TEST 3] Static QR Code Generation")
try:
    response = requests.post(f"{BASE_URL}/api/generate", data={
        "content": "Hello, this is a test!",
        "mode": "static",
        "access_code": ADMIN_PASSWORD,
        "size": 300,
        "error_correction": "M"
    })
    assert response.status_code == 200
    data = response.json()
    assert "qr_code_data_url" in data
    assert data["mode"] == "static"
    assert data["short_id"] is None
    print("✅ Static QR code generated successfully")
except Exception as e:
    print(f"❌ Static QR code failed: {e}")
    print(f"Response: {response.text if 'response' in locals() else 'N/A'}")
    exit(1)

# Test 4: Dynamic QR Code (Text Mode)
print("\n[TEST 4] Dynamic QR Code (Text Mode)")
try:
    long_content = "# 今日作业\n\n请完成以下练习：\n1. 阅读第三章\n2. 完成练习题\n3. 准备明天的讨论"
    response = requests.post(f"{BASE_URL}/api/generate", data={
        "content": long_content,
        "mode": "text",
        "access_code": ADMIN_PASSWORD,
        "size": 300,
        "error_correction": "M"
    })
    assert response.status_code == 200
    data = response.json()
    assert "qr_code_data_url" in data
    assert data["mode"] == "text"
    assert data["short_id"] is not None
    assert len(data["short_id"]) == 8

    # Test viewing the homework
    short_id = data["short_id"]
    view_response = requests.get(f"{BASE_URL}/v/{short_id}")
    assert view_response.status_code == 200
    assert "今日作业" in view_response.text
    print(f"✅ Dynamic QR code generated and viewable (ID: {short_id})")
except Exception as e:
    print(f"❌ Dynamic QR code failed: {e}")
    print(f"Response: {response.text if 'response' in locals() else 'N/A'}")
    exit(1)

# Test 5: Invalid Access Code
print("\n[TEST 5] Invalid Access Code")
try:
    response = requests.post(f"{BASE_URL}/api/generate", data={
        "content": "Test content",
        "mode": "static",
        "access_code": "wrong_password",
        "size": 300
    })
    assert response.status_code == 403
    print("✅ Invalid access code rejected correctly")
except Exception as e:
    print(f"❌ Access code test failed: {e}")
    exit(1)

# Test 6: Empty Content
print("\n[TEST 6] Empty Content Validation")
try:
    response = requests.post(f"{BASE_URL}/api/generate", data={
        "content": "",
        "mode": "static",
        "access_code": ADMIN_PASSWORD,
        "size": 300
    })
    assert response.status_code == 400
    print("✅ Empty content rejected correctly")
except Exception as e:
    print(f"❌ Empty content test failed: {e}")
    exit(1)

# Test 7: Stats API
print("\n[TEST 7] Stats API")
try:
    response = requests.get(f"{BASE_URL}/api/stats", params={
        "access_code": ADMIN_PASSWORD
    })
    assert response.status_code == 200
    data = response.json()
    assert "total_homeworks" in data
    assert data["total_homeworks"] >= 1
    print(f"✅ Stats API working (Total homeworks: {data['total_homeworks']})")
except Exception as e:
    print(f"❌ Stats API failed: {e}")
    exit(1)

# Test 8: Non-existent Homework
print("\n[TEST 8] Non-existent Homework")
try:
    response = requests.get(f"{BASE_URL}/v/nonexistent123")
    assert response.status_code == 404
    assert "作业不存在" in response.text or "not exist" in response.text.lower()
    print("✅ Non-existent homework handled correctly")
except Exception as e:
    print(f"❌ Non-existent homework test failed: {e}")
    exit(1)

print("\n" + "=" * 60)
print("✅ 所有测试通过!")
print("=" * 60)
print("\n📊 测试总结:")
print("  ✅ Health Check")
print("  ✅ Homepage Loading")
print("  ✅ Static QR Code Generation")
print("  ✅ Dynamic QR Code (Text Mode)")
print("  ✅ Invalid Access Code Protection")
print("  ✅ Empty Content Validation")
print("  ✅ Stats API")
print("  ✅ Error Handling")
print("\n🎉 系统准备就绪，可以开始使用!")
