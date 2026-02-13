"""
AI作业生成 - Prompt模板
"""

# ==================== 系统提示词 ====================
SYSTEM_PROMPT = """你是一位专业的英语教师，拥有丰富的教学经验和题目设计能力。
你的任务是根据用户的要求生成高质量的英语练习题。
所有题目必须符合指定年级的英语水平和课程标准。
输出必须是严格的JSON格式，不要有任何额外的文字说明。"""

# ==================== 题型Prompt模板 ====================

# 选择题
MULTIPLE_CHOICE_PROMPT = """请根据以下要求生成{count}道英语选择题：

**年级**：{grade}
**主题**：{topic}
**难度**：{difficulty}

**要求**：
1. 每道题包含：题干（question）、4个选项（options）、正确答案（answer）、中文解析（explanation）
2. 选项必须是A、B、C、D格式
3. 正确答案必须是单个字母（A/B/C/D）
4. 题目要符合{grade}学生的英语水平
5. 难度要符合{difficulty}级别（简单：基础知识点，中等：综合运用，困难：拓展提升）
6. 解析要简洁明了，用中文说明理由

**输出格式**（JSON）：
```json
{{
  "questions": [
    {{
      "question": "题干内容",
      "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
      "answer": "A",
      "explanation": "中文解析"
    }}
  ]
}}
```

请严格按照上述格式输出，不要添加任何其他文字。"""

# 填空题
FILL_IN_THE_BLANK_PROMPT = """请根据以下要求生成{count}道英语填空题：

**年级**：{grade}
**主题**：{topic}
**难度**：{difficulty}

**要求**：
1. 每道题包含：句子（sentence，用___表示空格）、答案（answer）、中文解析（explanation）
2. 空格必须是重点考察的知识点（词汇、语法、短语等）
3. 答案要准确，可以有多个正确答案（用/分隔）
4. 题目要符合{grade}学生的英语水平
5. 难度要符合{difficulty}级别
6. 解析要说明考察点和解题思路

**输出格式**（JSON）：
```json
{{
  "questions": [
    {{
      "sentence": "This is the place ___ I was born.",
      "answer": "where",
      "explanation": "考查定语从句。先行词是place，在从句中作地点状语，用where。"
    }}
  ]
}}
```

请严格按照上述格式输出，不要添加任何其他文字。"""

# 判断题
TRUE_FALSE_PROMPT = """请根据以下要求生成{count}道英语判断题：

**年级**：{grade}
**主题**：{topic}
**难度**：{difficulty}

**要求**：
1. 每道题包含：陈述句（statement）、正误（answer，True/False）、中文解析（explanation）
2. 陈述句要考查常见的语法规则、词汇用法或文化知识点
3. 答案必须是True或False
4. 题目要符合{grade}学生的英语水平
5. 难度要符合{difficulty}级别
6. 解析要说明判断理由

**输出格式**（JSON）：
```json
{{
  "questions": [
    {{
      "statement": "English is spoken by the largest number of people in the world.",
      "answer": "True",
      "explanation": "正确。英语是世界上使用最广泛的语言，作为母语和使用人数最多。"
    }}
  ]
}}
```

请严格按照上述格式输出，不要添加任何其他文字。"""

# 阅读理解
READING_COMPREHENSION_PROMPT = """请根据以下要求生成{count}篇英语阅读理解：

**年级**：{grade}
**主题**：{topic}
**难度**：{difficulty}

**要求**：
1. 每篇包含：文章（passage，150-250词）、题目（questions，3-5道）
2. 题目类型包括：细节理解题、推理判断题、词义猜测题、主旨大意题
3. 每道题包含：题干（question）、选项（options）、正确答案（answer）、解析（explanation）
4. 文章要符合{grade}学生的阅读水平
5. 难度要符合{difficulty}级别
6. 文章内容要贴近学生生活或有趣的文化知识

**输出格式**（JSON）：
```json
{{
  "passages": [
    {{
      "passage": "文章内容...",
      "title": "文章标题",
      "questions": [
        {{
          "question": "According to the passage, ...?",
          "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"],
          "answer": "B",
          "explanation": "根据文章第X段..."
        }}
      ]
    }}
  ]
}}
```

请严格按照上述格式输出，不要添加任何其他文字。"""

# 听力题（仅文本，v0.4.0添加音频）
LISTENING_PROMPT = """请根据以下要求生成{count}道英语听力题：

**年级**：{grade}
**主题**：{topic}
**难度**：{difficulty}

**要求**：
1. 每道题包含：听力文本（script，50-100词的对话或独白）、题目（question）、选项（options）、答案（answer）、解析（explanation）
2. 听力文本要口语化，符合真实对话场景
3. 题目要考查听力理解能力（细节、主旨、推理等）
4. 文本要符合{grade}学生的听力水平
5. 难度要符合{difficulty}级别

**输出格式**（JSON）：
```json
{{
  "questions": [
    {{
      "script": "M: What would you like to eat?\\nW: I'd like a hamburger, please.",
      "question": "What does the woman want to eat?",
      "options": ["A. A sandwich", "B. A hamburger", "C. A pizza", "D. A salad"],
      "answer": "B",
      "explanation": "女士说'I'd like a hamburger'，她想要汉堡。"
    }}
  ]
}}
```

请严格按照上述格式输出，不要添加任何其他文字。"""

# 作文/写作
ESSAY_WRITING_PROMPT = """请根据以下要求生成{count}个英语写作题目：

**年级**：{grade}
**主题**：{topic}
**难度**：{difficulty}

**要求**：
1. 每个题目包含：题目（title）、要求（requirements）、字数要求（word_count）、范文（sample，80-120词）、评分要点（grading_points）
2. 题目要贴近学生生活或社会热点
3. 要求要明确（内容要点、文体、时态等）
4. 范文要符合{grade}学生的写作水平
5. 难度要符合{difficulty}级别
6. 评分要点要列出3-5个关键评分标准

**输出格式**（JSON）：
```json
{{
  "questions": [
    {{
      "title": "My Favorite Season",
      "requirements": "请以'我最喜欢的季节'为题，写一篇英语作文。内容包括：1. 你最喜欢的季节 2. 喜欢的原因 3. 这个季节的活动",
      "word_count": "80-120词",
      "sample": "My favorite season is spring. The weather is warm and sunny...",
      "grading_points": ["内容完整，涵盖所有要点", "语法正确，句式多样", "词汇丰富，表达准确", "条理清晰，逻辑连贯"]
    }}
  ]
}}
```

请严格按照上述格式输出，不要添加任何其他文字。"""

# ==================== Prompt映射 ====================
PROMPT_TEMPLATES = {
    "choice": MULTIPLE_CHOICE_PROMPT,
    "fill_blank": FILL_IN_THE_BLANK_PROMPT,
    "true_false": TRUE_FALSE_PROMPT,
    "reading": READING_COMPREHENSION_PROMPT,
    "listening": LISTENING_PROMPT,
    "essay": ESSAY_WRITING_PROMPT
}

# ==================== 难度映射 ====================
DIFFICULTY_MAP = {
    "easy": "简单",
    "medium": "中等",
    "hard": "困难"
}

# ==================== 年级映射 ====================
GRADE_MAP = {
    "小学三年级": "Grade 3",
    "小学四年级": "Grade 4",
    "小学五年级": "Grade 5",
    "小学六年级": "Grade 6",
    "初中一年级": "Grade 7",
    "初中二年级": "Grade 8",
    "初中三年级": "Grade 9",
    "高中一年级": "Grade 10",
    "高中二年级": "Grade 11",
    "高中三年级": "Grade 12"
}
