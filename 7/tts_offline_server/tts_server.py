"""
医疗问答助手 - 离线版 TTS 代理服务
使用 Edge-TTS 实现本地语音合成
"""

from flask import Flask, request, jsonify, send_file, Response
import edge_tts
import asyncio
import os
import uuid
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置
TEMP_DIR = Path("temp_audio")
TEMP_DIR.mkdir(exist_ok=True)

# 默认配置
DEFAULT_VOICE = "zh-CN-YunyangNeural"  # 沉稳男声
DEFAULT_RATE = "+0%"
DEFAULT_PITCH = "+0Hz"
DEFAULT_VOLUME = "+0%"

# 可用语音列表
VOICES = {
    # 男声
    "zh-CN-YunyangNeural": "云扬 - 新闻男声（推荐）",
    "zh-CN-YunjianNeural": "云健 - 年轻男声",
    "zh-CN-YunxiNeural": "云希 - 活泼男声",
    "zh-CN-YunxiaNeural": "云夏 - 少年男声",
    # 女声
    "zh-CN-XiaoxiaoNeural": "晓晓 - 默认女声",
    "zh-CN-XiaoyiNeural": "小艺 - 温柔女声",
    "zh-CN-liaoning-XiaobeiNeural": "小北 - 东北女声",
    "zh-CN-shaanxi-XiaoniNeural": "小妮 - 陕西女声",
}


class TTSService:
    """TTS 服务类"""
    
    def __init__(self, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE, 
                 pitch: str = DEFAULT_PITCH, volume: str = DEFAULT_VOLUME):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.volume = volume
    
    async def synthesize_async(self, text: str, output_path: str = None) -> bytes:
        """异步生成语音"""
        if not output_path:
            filename = f"{uuid.uuid4().hex}.mp3"
            output_path = str(TEMP_DIR / filename)
        
        communicate = edge_tts.Communicate(text, self.voice, 
                                           rate=self.rate, 
                                           pitch=self.pitch, 
                                           volume=self.volume)
        await communicate.save(output_path)
        
        with open(output_path, 'rb') as f:
            audio_data = f.read()
        
        # 清理临时文件
        try:
            os.remove(output_path)
        except:
            pass
        
        return audio_data
    
    def synthesize(self, text: str, output_path: str = None) -> bytes:
        """同步生成语音"""
        return asyncio.run(self.synthesize_async(text, output_path))
    
    @staticmethod
    async def list_voices_async():
        """获取可用语音列表"""
        voices = await edge_tts.list_voices()
        chinese_voices = []
        for voice in voices:
            if voice['Locale'].startswith('zh'):
                chinese_voices.append({
                    'name': voice['Name'],
                    'locale': voice['Locale'],
                    'gender': voice['Gender'],
                    'short_name': voice['ShortName']
                })
        return chinese_voices
    
    @staticmethod
    def list_voices():
        """同步获取语音列表"""
        return asyncio.run(TTSService.list_voices_async())


# 全局 TTS 服务实例
tts_service = TTSService()


@app.route('/api/tts/voices', methods=['GET'])
def get_voices():
    """获取可用语音列表"""
    try:
        voices = TTSService.list_voices()
        return jsonify({
            'success': True,
            'voices': voices,
            'default': DEFAULT_VOICE
        })
    except Exception as e:
        logger.error(f"获取语音列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tts/synthesize', methods=['POST'])
def synthesize():
    """合成语音 - 返回二进制音频"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        voice = data.get('voice', DEFAULT_VOICE)
        rate = data.get('rate', DEFAULT_RATE)
        pitch = data.get('pitch', DEFAULT_PITCH)
        volume = data.get('volume', DEFAULT_VOLUME)
        
        if not text:
            return jsonify({
                'success': False,
                'error': '文本不能为空'
            }), 400
        
        # 创建临时服务实例
        service = TTSService(voice=voice, rate=rate, pitch=pitch, volume=volume)
        
        # 生成音频
        audio_data = service.synthesize(text)
        
        # 返回音频数据
        return Response(audio_data, mimetype='audio/mpeg', 
                       headers={'Content-Disposition': 'inline'})
    
    except Exception as e:
        logger.error(f"语音合成失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tts/save', methods=['POST'])
def synthesize_save():
    """合成语音 - 保存到文件"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        voice = data.get('voice', DEFAULT_VOICE)
        filename = data.get('filename', f"{uuid.uuid4().hex}.mp3")
        rate = data.get('rate', DEFAULT_RATE)
        pitch = data.get('pitch', DEFAULT_PITCH)
        volume = data.get('volume', DEFAULT_VOLUME)
        
        if not text:
            return jsonify({
                'success': False,
                'error': '文本不能为空'
            }), 400
        
        # 确保文件名安全
        filename = os.path.basename(filename)
        if not filename.endswith('.mp3'):
            filename += '.mp3'
        
        output_path = str(TEMP_DIR / filename)
        
        # 创建临时服务实例
        service = TTSService(voice=voice, rate=rate, pitch=pitch, volume=volume)
        
        # 生成音频
        service.synthesize_async(text, output_path)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'url': f'/api/tts/audio/{filename}'
        })
    
    except Exception as e:
        logger.error(f"语音保存失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tts/audio/<filename>', methods=['GET'])
def get_audio(filename):
    """获取音频文件"""
    try:
        filename = os.path.basename(filename)
        filepath = TEMP_DIR / filename
        
        if not filepath.exists():
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        return send_file(filepath, mimetype='audio/mpeg')
    
    except Exception as e:
        logger.error(f"获取音频失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tts/test', methods=['GET'])
def test_tts():
    """测试语音合成"""
    try:
        test_text = "您好，欢迎使用医疗问答助手。口服，一次3到6克，一日2到3次。"
        voice = request.args.get('voice', DEFAULT_VOICE)
        
        service = TTSService(voice=voice)
        audio_data = service.synthesize(test_text)
        
        return Response(audio_data, mimetype='audio/mpeg')
    
    except Exception as e:
        logger.error(f"测试失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'service': 'TTS Offline Server',
        'default_voice': DEFAULT_VOICE,
        'available_voices': len(VOICES)
    })


if __name__ == '__main__':
    print("=" * 50)
    print("医疗问答助手 - 离线 TTS 代理服务")
    print("=" * 50)
    print(f"默认语音: {DEFAULT_VOICE}")
    print(f"可用语音: {len(VOICES)} 种")
    print("=" * 50)
    print("API 接口:")
    print("  GET  /api/tts/voices      - 获取语音列表")
    print("  POST /api/tts/synthesize  - 合成语音(返回二进制)")
    print("  POST /api/tts/save        - 合成语音(保存文件)")
    print("  GET  /api/tts/test        - 测试语音")
    print("  GET  /health              - 健康检查")
    print("=" * 50)
    print("启动服务: http://localhost:5001")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5001, debug=False)
