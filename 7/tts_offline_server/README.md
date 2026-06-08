# 医疗问答助手 - 离线版本

基于知识库的医疗问答助手，**完全离线版本**，使用 Edge-TTS 本地语音合成。

## 功能特点

- **完全离线**: 无需联网即可使用
- **知识库问答**: 基于本地 Excel 知识库
- **语音播报**: 使用 Edge-TTS 本地合成（云扬-沉稳男声）
- **快捷问题**: 5行问题列表
- **智能推荐**: 推荐相关问题
- **登录验证**: 口令 `香连止痢丸`

## 项目结构

```
tts_offline_server/
├── app.py                 # Flask 后端主文件
├── knowledge_base.py       # 知识库处理模块
├── requirements.txt       # Python 依赖
├── README.md             # 本文档
│
├── templates/
│   ├── index.html         # 聊天页面
│   └── login.html        # 登录页面
│
└── data/                 # 知识库数据
    ├── question.xlsx      # 问题表
    └── answer.xlsx        # 答案表
```

## 快速启动

```bash
cd tts_offline_server

# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py

# 或使用启动脚本
./start.sh    # Linux/Mac
start.bat     # Windows
```

访问 http://localhost:5000

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页（需登录） |
| `/login` | GET/POST | 登录页面 |
| `/api/questions` | GET | 获取快捷问题 |
| `/api/ask` | POST | 问答接口 |
| `/api/recommend` | POST | 推荐问题 |
| `/api/tts/url` | POST | 语音合成（返回base64） |
| `/api/health` | GET | 健康检查 |

## 登录口令

```
香连止痢丸
```

## 语音配置

- **默认语音**: zh-CN-YunyangNeural（云扬-沉稳男声）
- **音频格式**: MP3
- **合成方式**: Edge-TTS 本地合成（首次使用会下载模型）

## 与在线版本区别

| 功能 | 在线版本 | 离线版本 |
|------|----------|----------|
| 知识库问答 | ✓ | ✓ |
| LLM 生成答案 | ✓ | ✗ |
| 语音合成 | 在线 TTS | Edge-TTS 本地 |
| 网络依赖 | 需要 | 不需要 |

## 首次使用

1. 首次运行会自动下载 Edge-TTS 模型（约 50MB）
2. 模型缓存位置: `~/.cache/edge-tts/`
3. 下载后可完全离线使用
