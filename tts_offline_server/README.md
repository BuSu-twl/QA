# 医疗问答助手 - 离线运行指南

## 概述

本项目是一个基于知识库的医疗问答助手，支持**完全离线运行**，无需网络连接即可使用知识库问答和语音合成功能。

## 文件结构

```
tts_offline_server/
├── app.py                 # Flask 后端主程序
├── knowledge_base.py      # 知识库处理模块
├── requirements.txt       # Python 依赖列表
│
├── templates/             # HTML 模板
│   ├── index.html         # 聊天页面
│   └── login.html         # 登录页面
│
├── data/                  # 知识库数据
│   ├── question.xlsx      # 问题表
│   └── answer.xlsx        # 答案表
│
├── models/                # 语音模型（可选）
│   └── zh-CN-YunyangNeural.mar  # 云扬语音模型
│
├── tts_server.py          # 独立 TTS 代理服务（可选）
├── start.sh               # Linux/Mac 启动脚本
├── start.bat              # Windows 启动脚本
└── README.md              # 说明文档
```

## 依赖安装

### 方式1：使用 requirements.txt

```bash
pip install -r requirements.txt
```

### 方式2：手动安装依赖

```bash
pip install flask openpyxl edge-tts
```

### 依赖说明

| 依赖包 | 版本 | 说明 |
|--------|------|------|
| flask | >=2.0 | Web 框架 |
| openpyxl | >=3.0 | Excel 文件读取 |
| edge-tts | >=6.0 | 语音合成 |

## 模型文件准备

### 方式1：从网络自动下载（首次需要网络）

首次运行 `python app.py` 时，edge-tts 会自动从微软服务器下载语音模型到缓存目录：

- Windows: `C:\Users\用户名\.cache\edge-tts\`
- Linux/Mac: `~/.cache/edge-tts/`

### 方式2：手动放置模型文件（完全离线）

#### 步骤1：创建 models 目录

```bash
mkdir models
```

#### 步骤2：获取 .mar 模型文件

从以下任一方式获取 `zh-CN-YunyangNeural.mar` 文件：

**方法A**：从已安装 edge-tts 的电脑复制
```bash
# 在有网络的电脑上
copy %USERPROFILE%\.cache\edge-tts\models\zh-CN-YunyangNeural.mar .\models\

# Linux/Mac
cp ~/.cache/edge-tts/models/zh-CN-YunyangNeural.mar ./models/
```

**方法B**：从其他来源获取模型文件

#### 步骤3：放置到项目目录

```
tts_offline_server/
├── models/
│   └── zh-CN-YunyangNeural.mar  ← 放置在此
├── app.py
└── ...
```

#### 步骤4：设置环境变量（可选）

app.py 已自动检测 `models/` 目录，如需手动设置：

**Windows CMD:**
```cmd
set EDGE_TTS_CACHE_DIR=D:\项目路径\tts_offline_server\models
python app.py
```

**Windows PowerShell:**
```powershell
$env:EDGE_TTS_CACHE_DIR="D:\项目路径\tts_offline_server\models"
python app.py
```

**Linux/Mac:**
```bash
export EDGE_TTS_CACHE_DIR=/项目路径/tts_offline_server/models
python app.py
```

## 启动方式

### 方式1：直接运行

```bash
python app.py
```

### 方式2：使用启动脚本

**Windows:**
```cmd
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

### 方式3：指定端口启动

```bash
python app.py --port 8080
```

## 访问地址

启动后访问：**http://localhost:5000**

登录口令：`香连止痢丸`

## 功能说明

### 已实现功能

| 功能 | 说明 | 离线可用 |
|------|------|---------|
| 登录验证 | 本地字符串比较 | ✓ |
| 知识库问答 | 匹配 Excel 中的问答 | ✓ |
| 语音合成 | Edge-TTS 本地合成 | ✓ |
| 推荐问题 | 基于关键词匹配 | ✓ |
| 快捷问题 | 分页显示 | ✓ |

### 待实现功能

| 功能 | 说明 | 备注 |
|------|------|------|
| LLM 生成答案 | 需要网络调用 | 离线版本不支持 |

## 知识库格式

### 问题表 (question.xlsx)

| 列 | 说明 |
|----|------|
| A列 | 问题ID（如"问题1"） |
| B列 | 问题内容 |

### 答案表 (answer.xlsx)

| 列 | 说明 |
|----|------|
| A列 | 问题ID（如"问题1答案"） |
| B列 | 答案内容 |

### 示例数据

**question.xlsx:**
| A | B |
|---|---|
| 问题1 | 该处方由哪些药材组成的？ |
| 问题2 | 该处方常规的用法用量？ |

**answer.xlsx:**
| A | B |
|---|---|
| 问题1答案 | 黄连、木香、槟榔等。 |
| 问题2答案 | 口服，一次3-6克，一日2-3次。 |

## 目录结构说明

```
tts_offline_server/
├── app.py                 # 主程序入口
├── knowledge_base.py      # 知识库加载和匹配逻辑
├── requirements.txt       # pip 依赖列表
│
├── templates/             # Flask 模板目录（不要改名）
│   ├── index.html         # 聊天界面
│   └── login.html         # 登录页面
│
├── data/                 # 数据目录（不要改名）
│   ├── question.xlsx      # 问题数据
│   └── answer.xlsx        # 答案数据
│
├── models/               # 模型目录（可选）
│   └── zh-CN-YunyangNeural.mar  # 语音模型
│
├── tts_server.py         # 独立 TTS 服务（可选，不需要）
└── ...
```

## 常见问题

### Q1: 提示 "edge-tts 未安装"

**解决:**
```bash
pip install edge-tts
```

### Q2: 语音合成失败

**解决:**
1. 确保 `models/` 目录存在
2. 确保 `zh-CN-YunyangNeural.mar` 文件存在
3. 或首次运行联网让 edge-tts 自动下载模型

### Q3: 找不到模板文件

**解决:**
确保 `app.py` 同目录下有 `templates/` 文件夹。

### Q4: 找不到知识库数据

**解决:**
确保 `app.py` 同目录下有 `data/` 文件夹，且包含 `question.xlsx` 和 `answer.xlsx`。

### Q5: 如何修改登录密码？

在 `app.py` 中修改第 X 行：
```python
if request.form.get('password') == '香连止痢丸':  # 修改这里
```

### Q6: 如何修改默认语音？

在 `app.py` 中修改第 48 行：
```python
TTS_VOICE = "zh-CN-YunyangNeural"  # 修改为其他语音
```

## 扩展：在其他项目中使用 knowledge_base.py

### 导入方式

```python
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from knowledge_base import (
    init_knowledge_base,
    find_best_match,
    get_recommended_questions,
    get_paginated_questions
)

# 初始化
init_knowledge_base()

# 查找答案
answer = find_best_match("用法用量")
print(f"答案: {answer}")

# 获取推荐
recommendations = get_recommended_questions("用法用量")
print(f"推荐: {recommendations}")

# 分页获取问题
result = get_paginated_questions(page=0, page_size=10)
print(f"问题列表: {result['questions']}")
```

### API 返回格式

```python
# get_paginated_questions 返回
{
    'success': True,
    'questions': ['问题1', '问题2', ...],
    'total': 11,
    'page': 0,
    'page_size': 10,
    'total_pages': 2
}

# find_best_match 返回
"口服，一次3-6克，一日2-3次。"

# get_recommended_questions 返回
['该处方由哪些药材组成的？', '该处方适用于哪些病症？', ...]
```

## 版本信息

- 语音: zh-CN-YunyangNeural（云扬-沉稳男声）
