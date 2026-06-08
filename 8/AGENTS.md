# 医疗问答助手项目

## 项目概述
基于知识库的医疗问答助手，使用 Python Flask 实现，支持语音播报和智能推荐。

## 技术栈
- **后端**: Python Flask
- **前端**: 原生 HTML/CSS/JavaScript
- **知识库**: Excel 文件 (openpyxl)
- **语音合成**: Edge-TTS (离线模式)
- **离线版本**: tts_offline_server/（完全离线，无需网络）

## 项目结构

```
/workspace/projects/
├── app.py                      # Flask 后端主文件
├── knowledge_base.py            # 知识库处理模块
│
├── templates/
│   ├── index.html              # 聊天页面
│   └── login.html              # 登录页面
│
├── tts/                        # 语音合成测试
│   ├── tts_demo.py             # Pyttsx3 测试（完全离线）
│   ├── edge_tts_demo.py        # Edge-TTS 测试
│   ├── offline_tts_analysis.md # 离线TTS方案分析
│   ├── edge_tts_offline.py     # Edge-TTS 离线模式模块（可导入）
│   │
│   └── tts_offline/            # Edge-TTS 离线模式完整包
│       ├── edge_offline.py     # 主程序（命令行工具）
│       ├── edge_tts_offline.py # 原Edge-TTS测试
│       ├── silero_tts_demo.py  # Silero TTS测试
│       ├── EDGE_TTS_MODEL_DOWNLOAD.md  # 模型下载指南
│       ├── models/cache/       # 缓存的语音模型
│       └── output/             # 生成的音频文件
│
├── tts_offline_server/         # 离线版本问答助手 ⭐
│   ├── app.py                 # Flask 后端（离线版本）
│   ├── knowledge_base.py       # 知识库模块
│   ├── requirements.txt        # Python 依赖
│   ├── start.sh               # Linux/Mac 启动脚本
│   ├── start.bat              # Windows 启动脚本
│   ├── README.md              # 使用文档
│   ├── templates/
│   │   ├── index.html         # 聊天页面
│   │   └── login.html         # 登录页面
│   └── data/                  # 知识库数据
│       ├── question.xlsx      # 问题表
│       └── answer.xlsx        # 答案表
│
└── data/
    └── 问答知识库.xlsx          # 知识库 Excel 文件
```

## 核心功能

### 1. 登录功能
- 访问口令：`香连止痢丸`
- 登录成功后将跳转到聊天页面
- 使用 Flask session 记录登录状态

### 2. 知识库问答
- 从 Excel 读取问题表和答案表
- 支持问题模糊匹配
- 知识库无答案时调用 LLM 生成（需要网络）

### 3. 语音播报
- 使用 Edge-TTS 合成语音（默认：zh-CN-YunyangNeural 新闻男声）
- 自动播放答案语音
- 播放时显示张嘴头像，停止时显示闭嘴头像
- 每个回答气泡有独立的播放/暂停/停止控制

### 4. 快捷问题
- 固定显示5行问题列表
- 每行一个问题
- 点击问题填充到输入框
- 已发送问题显示为蓝色

### 5. 智能推荐
- 根据用户问题推荐相关问题
- 显示在回答气泡下方
- 点击标签填充到输入框
- 过滤已询问过的问题

## API 接口

### POST /login
登录接口
- 参数: `{ password }`
- 返回: 成功返回聊天页面，失败返回登录页并显示错误

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
- 返回: `{ success, audio_url }` (base64 编码的音频)

## 启动命令

```bash
# 开发环境
coze dev

# 生产环境
coze build && coze start
```

## TTS 语音方案

| 方案 | 离线程度 | 中文效果 | 集成难度 |
|------|----------|----------|----------|
| **Edge-TTS** | 首次下载后离线 | 优秀 | 简单 |
| Pyttsx3 | 完全离线 | 一般 | 简单 |
| Silero TTS | 完全离线 | 良好 | 中等 |

### 推荐语音
- **zh-CN-YunyangNeural** - 新闻男声，专业沉稳（医疗场景推荐）

### TTS 测试使用方法

```bash
cd /workspace/projects/tts/tts_offline

# 查看语音列表
python edge_offline.py --list

# 下载模型（首次使用）
python edge_offline.py --download

# 运行测试
python edge_offline.py

# 生成自定义文本
python edge_offline.py --text "口服，一次3到6克"
```

## 已知问题修复记录

### 1. 重复回答 Bug
**问题**: 同一问题发送后出现多个回答气泡
**原因**: `sendQuestion` 函数缺少防重复发送机制
**修复**: 添加 `isSending` 标志防止重复调用

### 2. messageId 作用域错误
**问题**: `addMessage` 函数中 `messageId` 在 else 块外无法访问
**修复**: 将 `messageId` 声明移到函数开头

### 3. 暂停按钮不显示
**问题**: 暂停按钮无法显示和操作
**修复**: 修改 `updateSingleButtonState` 函数，正确切换播放/暂停按钮显示状态

### 4. 暂停后继续播放从头开始
**问题**: 暂停后点击播放按钮，音频从头开始播放
**修复**: 在 `playAudio` 函数中复用已暂停的音频对象
