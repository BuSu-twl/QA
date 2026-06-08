# 离线语音合成（TTS）方案分析

## 需求
将当前的在线 TTS（依赖 coze 服务）改造为离线方案，支持不联网时也能语音播报。

---

## 方案一：Pyttsx3（推荐）

### 简介
纯 Python 的跨平台 TTS 库，使用操作系统内置的语音引擎，无需网络。

### 特点
- ✅ **完全离线**：使用系统自带语音
- ✅ **无需 API Key**
- ✅ **安装简单**：`pip install pyttsx3`
- ✅ **响应快速**：本地合成
- ❌ 音质一般：机械感较强
- ❌ 中文支持依赖系统

### 安装
```bash
pip install pyttsx3
```

### 使用示例
```python
import pyttsx3

def text_to_speech(text, output_file='output.mp3'):
    engine = pyttsx3.init()
    # 设置中文语音（如果系统支持）
    voices = engine.getProperty('voices')
    for voice in voices:
        if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
            engine.setProperty('voice', voice.id)
            break
    # 保存为音频文件
    engine.save_to_file(text, output_file)
    engine.runAndWait()
```

### 系统要求
- **Windows**: 自带中文语音，直接可用
- **macOS**: 需要下载中文语音（系统偏好设置 > 语音）
- **Linux**: 需要安装 `espeak` 和中文语音包

---

## 方案二：Silero TTS

### 简介
Silero 公司提供的开源神经网络 TTS，音质优秀，提供离线模型。

### 特点
- ✅ **完全离线**：模型本地运行
- ✅ **音质好**：基于深度学习
- ✅ **多语言**：支持中文
- ✅ **免费商用**
- ❌ 模型较大（首次下载约 100MB）
- ❌ 需要 GPU 加速（可选，CPU 也可运行但较慢）

### 安装
```bash
pip install silero-tts
```

### 使用示例
```python
import torch
from silero_tts import load_model, load_audio

# 加载模型
device = torch.device('cpu')
model = load_model(device)

# 合成语音
sample_rate = 24000
speaker = 'aidar'  # 或 'baya', 'xenia', 'kseniya' 等

audio = model.apply_tts(
    text="口服，一次3-6克，一日2-3次。",
    speaker=speaker,
    sample_rate=sample_rate
)

# 保存为 WAV 文件
import numpy as np
from scipy.io import wavfile
wavfile.write('output.wav', sample_rate, audio.numpy())
```

---

## 方案三：Edge-TTS 离线模式

### 简介
微软 Edge 浏览器的 TTS 技术，可以通过下载 voice 模型实现离线。

### 特点
- ✅ **音质好**：微软高品质语音
- ✅ **中文支持好**
- ✅ **可下载离线 voices**
- ❌ 需要先下载 voice 文件
- ❌ 部分 voice 可能需要联网验证

### 安装
```bash
pip install edge-tts
```

### 使用示例
```python
import asyncio
from edge_tts import Communicate

async def main():
    communicate = Communicate(
        text="口服，一次3-6克，一日2-3次。",
        voice="zh-CN-XiaoxiaoNeural"  # 使用本地缓存的 voice
    )
    await communicate.save("output.mp3")

asyncio.run(main())
```

---

## 方案四：PaddleSpeech

### 简介
百度飞桨开源的语音技术，包含 TTS 功能。

### 特点
- ✅ **完全离线**
- ✅ **百度技术积累**
- ✅ **中文优化**
- ❌ 安装复杂（依赖 PaddlePaddle）
- ❌ 模型较大
- ❌ CPU 性能要求较高

### 安装
```bash
pip install paddlespeech paddlespeech-inference
```

---

## 方案对比

| 方案 | 离线程度 | 中文支持 | 音质 | 安装复杂度 | 推荐度 |
|------|----------|----------|------|------------|--------|
| Pyttsx3 | 完全离线 | 一般 | 机械感 | 简单 | ⭐⭐⭐ |
| Silero TTS | 完全离线 | 好 | 优秀 | 中等 | ⭐⭐⭐⭐ |
| Edge-TTS | 需下载 | 优秀 | 优秀 | 中等 | ⭐⭐⭐⭐ |
| PaddleSpeech | 完全离线 | 优秀 | 优秀 | 复杂 | ⭐⭐⭐ |

---

## 推荐方案

### 最佳选择：**Pyttsx3** 或 **Silero TTS**

**如果追求简单快速**：选择 Pyttsx3
- 安装简单
- 依赖少
- 适合轻量级使用

**如果追求音质**：选择 Silero TTS
- 音质最佳
- 完全免费
- 模型一次下载后可离线使用

---

## 实施建议

### 集成到当前项目（Flask）

如果选择 Pyttsx3，集成方式：

1. 安装依赖：
```bash
pip install pyttsx3 flask
```

2. 修改 `app.py` 中的 TTS 接口：
```python
import pyttsx3
import base64
import io

def local_tts(text):
    """本地语音合成"""
    engine = pyttsx3.init()
    # 配置中文语音
    for voice in engine.getProperty('voices'):
        if 'chinese' in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break
    engine.setProperty('rate', 150)  # 语速
    engine.setProperty('volume', 1.0)  # 音量
    
    # 合成到内存
    mp3_fp = io.BytesIO()
    # pyttsx3 不直接支持输出到内存，需要用 WAV 转换
    engine.save_to_file(text, '/tmp/temp_audio.wav')
    engine.runAndWait()
    
    # 读取并转为 base64
    with open('/tmp/temp_audio.wav', 'rb') as f:
        audio_data = base64.b64encode(f.read()).decode()
    
    return f"data:audio/wav;base64,{audio_data}"
```

---

## 注意事项

1. **音频格式转换**：Pyttsx3 默认输出 WAV 格式，需要可播放的 MP3 可用 `pydub` 转换
2. **系统语音安装**：确保操作系统已安装中文语音
3. **权限问题**：Linux 下可能需要配置音频服务（如 PulseAudio）

---

## 结论

**完全可行**。推荐使用 **Pyttsx3** 进行离线 TTS 改造：
- 安装简单
- 依赖少
- 完全离线
- 适合当前项目需求

如需更高音质，可选择 **Silero TTS**。
