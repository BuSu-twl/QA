# Edge-TTS 离线模型下载指南

## 概述

Edge-TTS 的离线模式本质上是将微软服务器的语音模型缓存到本地，之后合成时直接从本地读取模型，无需联网。

## 模型下载方法

### 方法一：使用 Demo 程序自动下载

```bash
cd /workspace/projects/edge_tts_offline

# 下载所有中文语音模型
python edge_offline.py --download

# 下载指定语音模型
python edge_offline.py --download --voice zh-CN-YunyangNeural
```

### 方法二：手动下载模型

Edge-TTS 使用 `.mar` 格式的模型文件。中文语音模型可以从以下方式获取：

#### 1. 通过 edge-tts Python 包获取

```python
# list_voices.py
import asyncio
import edge_tts
from pathlib import Path

async def download_models():
    """列出并下载所有中文语音模型"""
    voices = await edge_tts.list_voices()

    chinese_voices = [v for v in voices if v['Locale'].startswith('zh')]

    for voice in chinese_voices:
        print(f"语音: {voice['Name']}")
        print(f"  语言: {voice['Locale']}")
        print(f"  性别: {voice['Gender']}")
        print(f"  模型URL: {voice.get(' FriendlyName', 'N/A')}")

    # 获取模型URL
    communicate = edge_tts.Communicate("测试", voice['Name'])
    # 模型会自动下载到 ~/.cache/edge-tts/

asyncio.run(download_models())
```

#### 2. 从缓存目录获取

```bash
# 查找缓存目录
python -c "import os; print(os.path.expanduser('~/.cache/edge-tts/'))"

# 复制缓存到项目目录
cp -r ~/.cache/edge-tts/ ./models/
```

## 模型文件说明

### 缓存目录结构

```
~/.cache/edge-tts/
├── voices/
│   ├── zh-CN-XiaoxiaoNeural.mar       # 晓晓（女声）
│   ├── zh-CN-XiaoyiNeural.mar         # 小艺（女声）
│   ├── zh-CN-YunjianNeural.mar        # 云健（男声）
│   ├── zh-CN-YunxiNeural.mar          # 云希（男声）
│   ├── zh-CN-YunxiaNeural.mar         # 云夏（女声）
│   ├── zh-CN-YunyangNeural.mar        # 云扬（男声）⭐ 推荐
│   ├── zh-CN-liaoning-XiaobeiNeural.mar  # 东北话（女声）
│   └── zh-CN-shaanxi-XiaoniNeural.mar    # 陕西话（女声）
└── data/
    └── ...
```

### 模型文件大小

| 语音 | 文件名 | 大小（估算） | 说明 |
|------|--------|-------------|------|
| 晓晓 | zh-CN-XiaoxiaoNeural.mar | ~50MB | 女声，年轻自然 |
| 小艺 | zh-CN-XiaoyiNeural.mar | ~50MB | 女声，活泼可爱 |
| 云健 | zh-CN-YunjianNeural.mar | ~50MB | 男声，年轻活力 |
| 云希 | zh-CN-YunxiNeural.mar | ~50MB | 男声，自然流畅 |
| **云扬** | zh-CN-YunyangNeural.mar | ~50MB | 男声，新闻播报 |
| 云夏 | zh-CN-YunxiaNeural.mar | ~50MB | 女声，温柔亲切 |

## 医疗场景推荐

### 推荐语音

| 排名 | 语音 | 特点 | 适用场景 |
|------|------|------|----------|
| 1 | **YunyangNeural** | 新闻男声，专业沉稳 | 医疗问答、药品说明 |
| 2 | YunxiNeural | 年轻男声，自然流畅 | 健康咨询 |
| 3 | YunjianNeural | 活力男声 | 年轻人健康建议 |
| 4 | XiaoxiaoNeural | 知性女声 | 护理指导 |

### 为什么推荐云扬（YunyangNeural）

1. **专业感强** - 新闻播报风格，适合医疗健康场景
2. **发音清晰** - 字正腔圆，医疗术语更易听懂
3. **沉稳可信** - 给用户专业可靠的感受

## 离线使用步骤

### 步骤 1：在有网络的电脑上下载模型

```bash
# 安装 edge-tts
pip install edge-tts

# 运行下载脚本
cd /workspace/projects/edge_tts_offline
python edge_offline.py --download
```

### 步骤 2：打包模型文件

```bash
# 复制模型到项目目录
mkdir -p offline_models
cp -r ~/.cache/edge-tts/ ./offline_models/

# 或者直接复制整个缓存目录
cp -r ~/.cache/edge-tts/ ./models/cache/

# 压缩打包（可选）
tar -czvf edge_tts_models.tar.gz ./offline_models/
```

### 步骤 3：在离线电脑上使用

```bash
# 解压模型（如果压缩过）
tar -xzvf edge_tts_models.tar.gz

# 设置环境变量
export EDGE_TTS_CACHE_DIR="./offline_models/voices"

# 运行合成
python edge_offline.py --text "口服，一次3到6克，一日2到3次"
```

## Windows 环境注意事项

### 缓存目录位置

Windows 系统的缓存目录在：
```
C:\Users\<用户名>\AppData\Local\Temp\edge-tts\
# 或
%LOCALAPPDATA%\Temp\edge-tts\
```

### 查找缓存目录

```python
import tempfile
import os

cache_dir = os.path.join(tempfile.gettempdir(), 'edge-tts')
print(f"Edge-TTS 缓存目录: {cache_dir}")
```

## 常见问题

### Q1: 模型下载失败？

```bash
# 检查网络连接
curl https://speech.platform.bing.com

# 使用代理（如果有）
export https_proxy="http://proxy:port"
python edge_offline.py --download
```

### Q2: 模型文件损坏？

```bash
# 删除损坏的缓存
rm -rf ~/.cache/edge-tts/

# 重新下载
python edge_offline.py --download
```

### Q3: 如何验证模型已正确下载？

```python
import os

cache_dir = os.path.expanduser('~/.cache/edge-tts/voices')
models = [f for f in os.listdir(cache_dir) if f.endswith('.mar')]

print(f"已下载 {len(models)} 个语音模型:")
for model in models:
    path = os.path.join(cache_dir, model)
    size = os.path.getsize(path) / (1024*1024)  # MB
    print(f"  {model}: {size:.1f}MB")
```

### Q4: 模型可以共享给其他人吗？

**可以**。Edge-TTS 的 `.mar` 模型文件是通用的，可以复制到其他电脑使用。

## 性能说明

| 指标 | 数值 | 说明 |
|------|------|------|
| 首次合成 | 3-10秒 | 需要联网下载模型 |
| 后续合成 | <1秒 | 使用本地缓存模型 |
| 模型大小 | ~50MB/语音 | 每个 .mar 文件 |
| 支持时长 | 无限制 | 长文本自动分段 |

## 参考链接

- [Edge-TTS GitHub](https://github.com/rany2/edge-tts)
- [微软语音服务文档](https://learn.microsoft.com/zh-cn/azure/cognitive-services/speech-service/index-text-to-speech)
- [讯飞离线语音合成](https://www.xfyun.cn/) (备选方案)
