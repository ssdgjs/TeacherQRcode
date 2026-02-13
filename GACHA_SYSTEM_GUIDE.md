# 音频抽卡系统 - 使用指南

## 功能概述

"音频抽卡"系统为教师提供了强大的二次编辑能力，支持：

1. **AI 音色推荐** - 根据对话内容自动推荐最合适的音色配置
2. **多版本管理** - 保存每次生成的结果，可以随时切换
3. **粒度控制** - 支持整作业抽卡或单个题目抽卡
4. **上下文记忆** - 最多保留最近 5 次的抽卡历史，优化生成质量
5. **自定义提示词** - 教师可以输入具体需求来引导 AI 生成

---

## 数据模型

### GenerationHistory 表

```sql
CREATE TABLE generation_history (
    id INTEGER PRIMARY KEY,
    homework_id INTEGER NOT NULL,          -- 关联的作业ID
    user_id INTEGER NOT NULL,              -- 用户ID
    version INTEGER NOT NULL,              -- 版本号
    content TEXT NOT NULL,                 -- 完整的生成内容（JSON）
    prompt TEXT,                           -- 使用的提示词
    previous_context TEXT,                 -- 之前的历史上下文
    voice_config TEXT,                     -- 音色配置（仅听力题）
    is_active BOOLEAN DEFAULT TRUE,        -- 是否是当前使用的版本
    created_at TIMESTAMP,                  -- 创建时间
    metadata TEXT                          -- 额外元数据
);
```

---

## API 端点

### 1. 获取抽卡历史

**端点**: `GET /api/v1/homework/{homework_id}/history`

**说明**: 获取某个作业的所有抽卡历史记录

**响应示例**:
```json
{
  "success": true,
  "data": {
    "homework_id": 123,
    "histories": [
      {
        "id": 1,
        "version": 1,
        "content": {...},
        "prompt": "生成10道选择题",
        "voice_config": "{\"M\": \"en-US-ChristopherNeural\", \"W\": \"en-US-AriaNeural\"}",
        "is_active": false,
        "created_at": "2026-02-11T12:00:00"
      },
      {
        "id": 2,
        "version": 2,
        "content": {...},
        "prompt": "题目要更简单一些",
        "voice_config": "{\"M\": \"en-US-EricNeural\", \"W\": \"en-US-JennyNeural\"}",
        "is_active": true,
        "created_at": "2026-02-11T12:05:00"
      }
    ],
    "total": 2
  }
}
```

---

### 2. 重新抽卡（整个作业）

**端点**: `POST /api/v1/homework/{homework_id}/regenerate`

**参数**:
- `custom_prompt` (可选): 自定义提示词
- `voice_config` (可选): 音色配置（JSON 格式）

**请求示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/homework/123/regenerate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "custom_prompt": "题目要更简单一些，适合初学者",
    "voice_config": "{\"M\": \"en-US-EricNeural\", \"W\": \"en-US-JennyNeural\"}"
  }'
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "homework_id": 123,
    "content": {...},
    "version": 3,
    "message": "重新生成成功"
  }
}
```

---

### 3. 重新抽卡（单个题目）

**端点**: `POST /api/v1/homework/{homework_id}/regenerate-question`

**参数**:
- `question_index` (必需): 题目索引（从 0 开始）
- `custom_prompt` (可选): 自定义提示词
- `voice_config` (可选): 音色配置

**请求示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/homework/123/regenerate-question" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question_index": 0,
    "custom_prompt": "这道题太难了，请简化",
    "voice_config": "{\"M\": \"en-US-GuyNeural\", \"W\": \"en-US-AriaNeural\"}"
  }'
```

---

### 4. 选择历史版本

**端点**: `POST /api/v1/homework/{homework_id}/select/{history_id}`

**说明**: 将某个历史版本设置为当前使用版本

**请求示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/homework/123/select/2" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "homework_id": 123,
    "selected_version": 2,
    "history_id": 2,
    "message": "已切换到版本 2"
  }
}
```

---

## 音色推荐系统

### 预设场景

系统提供了 6 种预设场景：

| 场景 | 适用场景 | 特点 |
|------|---------|------|
| `default` | 通用场景 | 均衡配置，适合大多数情况 |
| `school` | 校园场景 | 老师（成年专业）和学生（年轻活泼） |
| `medical` | 医疗场景 | 医生（专业稳重）和患者（自然亲切） |
| `shopping` | 购物场景 | 店员（热情友好）和顾客 |
| `family` | 家庭场景 | 父母（温和）和孩子（活泼） |
| `business` | 商务场景 | 专业商务人士对话 |

### 使用示例

```python
from ai_service import get_voice_recommender

# 获取推荐服务
recommender = get_voice_recommender()

# 分析对话并推荐音色
dialogue = """
M: Good morning, Mrs. Smith. I'm Dr. Johnson.
W: Good morning, doctor. I have a terrible headache.
M: Let me examine you. When did it start?
W: Since yesterday morning.
"""

recommendation = recommender.recommend_voice_config(dialogue)

print(f"推荐预设: {recommendation['preset_name']}")
print(f"置信度: {recommendation['confidence']}")
print(f"推荐理由: {recommendation['reasoning']}")
print(f"音色映射: {recommendation['voice_map']}")
```

输出：
```
推荐预设: 医疗场景
置信度: 0.85
推荐理由: 根据对话内容检测到'医疗场景'场景，推荐使用相应音色配置。
音色映射: {
  'M': 'en-US-GuyNeural',
  'W': 'en-US-JennyNeural'
}
```

---

## 前端集成

### 基本使用

在 HTML 页面中引入抽卡历史组件：

```html
<div id="gacha-history-container"></div>

<script>
// 加载某个作业的抽卡历史
loadGachaHistory(homeworkId);
</script>
```

### 显示音色选择器

```javascript
// 显示音色选择器
showVoiceSelector(homeworkId);

// 针对特定题目显示音色选择器
showVoiceSelector(homeworkId, questionIndex);
```

### 重新抽卡

```javascript
// 重新生成整个作业
regenerateHomework(homeworkId);

// 重新生成单个题目
regenerateQuestion(homeworkId, questionIndex);
```

---

## 工作流程

### 典型使用场景

1. **初次生成**
   ```
   教师输入参数 → AI 生成题目 → 系统推荐音色 → 生成音频 → 保存版本1
   ```

2. **查看结果，不满意**
   ```
   教师浏览作业 → 点击"查看历史" → 查看所有版本
   ```

3. **调整单个题目**
   ```
   选择第 3 题 → 点击"重新生成" → 输入提示词 → 生成新版本
   ```

4. **调整音色**
   ```
   点击"音色配置" → 选择场景（如"校园"） → 系统推荐音色 → 确认重新生成
   ```

5. **版本切换**
   ```
   查看历史列表 → 选择版本 2 → 点击"切换到此版本" → 确认
   ```

---

## 上下文管理

### 自动上下文构建

系统会自动构建最近 5 次的抽卡历史作为上下文：

```
版本 1
提示词: 生成10道选择题
音色配置: {"M": "en-US-ChristopherNeural", "W": "en-US-AriaNeural"}

---

版本 2
提示词: 题目要更简单一些
音色配置: {"M": "en-US-EricNeural", "W": "en-US-JennyNeural"}

---

版本 3
提示词: 第3题太难了，请简化
音色配置: {"M": "en-US-EricNeural", "W": "en-US-JennyNeural"}
```

这个上下文会作为 `previous_context` 参数传递给 AI，帮助它理解之前的修改意图。

### 上下文长度限制

- **最多保留**: 5 次历史记录
- **超出处理**: 自动删除最旧的记录，保留最近 5 次
- **目的**: 控制上下文长度，避免超出 AI 模型的 token 限制

---

## 音色配置格式

### JSON 格式

```json
{
  "M": "en-US-ChristopherNeural",
  "W": "en-US-AriaNeural",
  "Doctor": "en-US-GuyNeural",
  "Patient": "en-US-JennyNeural"
}
```

### 可用音色列表

#### 男性声音
- `en-US-GuyNeural` - 深沉稳重
- `en-US-ChristopherNeural` - 专业温和
- `en-US-BrianNeural` - 专业商务
- `en-US-EricNeural` - 年轻活泼

#### 女性声音
- `en-US-AriaNeural` - 自然亲切
- `en-US-JennyNeural` - 热情友好
- `en-US-MichelleNeural` - 专业温和

---

## 注意事项

1. **额度消费**
   - 每次抽卡（无论整作业还是单题目）都会消耗 1 个额度
   - 切换历史版本不消耗额度

2. **音频文件管理**
   - 每次重新生成听力题时，会创建新的音频文件
   - 历史版本的音频文件会保留
   - 建议定期清理不需要的版本

3. **并发限制**
   - 同一作业同时只能进行一次抽卡操作
   - 建议等待上一次抽卡完成后再开始下一次

4. **音色配置建议**
   - 优先使用系统推荐的预设场景
   - 可以在推荐基础上微调
   - 听力题建议使用不同性别的声音以增强辨识度

---

## 扩展功能

### 未来计划

1. **情感控制**
   - 支持为对话添加情感标签（高兴、悲伤、愤怒等）
   - AI 根据情感调整语音语调

2. **语速控制**
   - 支持为不同说话者设置不同语速
   - 模拟真实对话中的语速变化

3. **批量操作**
   - 支持一次选择多个题目进行批量重新生成
   - 支持批量应用音色配置

4. **版本对比**
   - 并排显示两个版本的差异
   - 高亮显示变化的部分

5. **版本合并**
   - 支持从不同版本中选择题目组合成新版本
   - 类似" cherry-pick" 功能

---

## 故障排查

### 常见问题

**Q: 重新生成后音色没有变化？**

A: 检查 `voice_config` 参数是否正确传递。确保 JSON 格式有效，音色名称正确。

**Q: 历史记录不显示？**

A: 确认已登录且是作业的创建者。检查 API 返回的错误信息。

**Q: 切换版本后内容没更新？**

A: 刷新页面或重新加载作业内容。检查 `is_active` 标志是否正确设置。

**Q: 音色推荐不准确？**

A: 可以手动调整音色配置，或者提供更详细的场景描述。

---

## 开发者指南

### 数据库迁移

如果需要添加 `generation_history` 表到现有数据库：

```python
from models import SQLModel, GenerationHistory
from database import engine

# 创建表
SQLModel.metadata.create_all(engine)
```

### 测试 API

```bash
# 测试获取历史
curl "http://localhost:8000/api/v1/homework/1/history" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 测试重新生成
curl -X POST "http://localhost:8000/api/v1/homework/1/regenerate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"custom_prompt": "让题目更简单"}'
```

---

## 更新日志

### v1.0.0 (2026-02-11)

- ✅ 实现抽卡历史数据模型
- ✅ 添加抽卡相关 API 接口
- ✅ 创建前端抽卡历史组件
- ✅ 实现音色推荐系统
- ✅ 支持上下文记忆（最多 5 次）
- ✅ 支持整作业和单题目抽卡
- ✅ 支持版本切换

---

## 支持

如有问题或建议，请联系开发团队或提交 Issue。
