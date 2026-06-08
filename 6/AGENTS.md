# 医疗问答助手项目

## 项目概述
基于知识库的医疗问答助手，使用 Python Flask 实现，集成 LLM 和 TTS 功能。

## 技术栈
- **后端**: Python Flask
- **前端**: 原生 HTML/CSS/JavaScript
- **AI 集成**: coze-coding-dev-sdk (LLM + TTS)
- **知识库**: Excel 文件 (openpyxl)

## 项目结构
```
/workspace/projects/
├── app.py              # Flask 后端主文件
├── knowledge_base.py    # 知识库处理模块
├── templates/
│   ├── index.html      # 聊天页面 (需登录)
│   └── login.html      # 登录页面
├── static/
│   ├── avatar_closed.png  # 闭嘴头像
│   └── avatar_open.png    # 张嘴头像
└── knowledge_base/
    └── 问答知识库.xlsx    # 知识库 Excel 文件
```

## 核心功能

### 1. 登录功能
- 访问口令：`香连止痢丸`
- 登录成功后将跳转到聊天页面
- 使用 Flask session 记录登录状态

### 2. 知识库问答
- 从 Excel 读取问题表和答案表
- 支持问题模糊匹配
- 知识库无答案时调用 LLM 生成

### 2. 语音播报
- 使用 TTS 合成语音 (zh_male_m191_uranus_bigtts)
- 自动播放答案语音
- 播放时显示张嘴头像，停止时显示闭嘴头像
- 每个回答气泡有独立的播放/暂停/停止控制

### 3. 快捷问题
- 5行5行分页显示问题列表
- 点击问题自动填充输入框
- 已发送问题显示为灰色

### 4. 智能推荐
- 根据用户问题推荐相关问题
- 显示在输入框下方

## API 接口

### POST /login
登录接口
- 参数: `{ password }`
- 返回: `{ success, redirect }` 或 `{ success: false, error }`

### GET /api/questions
获取快捷问题列表
- 参数: `page` (页码), `page_size` (每页数量)
- 返回: `{ success, questions, total, page, page_size, total_pages }`

### POST /api/ask
处理用户提问
- 参数: `{ question }`
- 返回: `{ success, answer, source, question }`
- source: `knowledge_base` (知识库) | `llm` (AI助手)

### POST /api/recommend
智能推荐相关问题
- 参数: `{ question }`
- 返回: `{ success, recommendations }`

### POST /api/tts/url
语音合成
- 参数: `{ text }`
- 返回: `{ success, audio_url }`

## 启动命令
```bash
# 开发环境
coze dev

# 生产环境
coze build && coze start
```

## 已知问题修复记录

### 1. 重复回答 Bug
**问题**: 同一问题发送后出现多个回答气泡
**原因**: `sendQuestion` 函数缺少防重复发送机制
**修复**: 添加 `isSending` 标志防止重复调用

### 2. messageId 作用域错误
**问题**: `addMessage` 函数中 `messageId` 在 else 块外无法访问
**修复**: 将 `messageId` 声明移到函数开头，else 块内赋值
