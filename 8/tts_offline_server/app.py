"""
基于知识库的问答助手 - Flask 后端（离线版本）
使用 Edge-TTS 离线语音合成
"""
import os
import sys
import logging
import asyncio
from flask import Flask, render_template, request, jsonify, session, redirect
import base64

# 添加父目录到路径，以便导入 knowledge_base
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tts_offline_server.knowledge_base import (
    load_answers_from_excel,
    get_paginated_questions,
    get_recommended_questions,
    find_best_match,
    init_knowledge_base
)

# 尝试导入 edge-tts
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logging.warning("edge-tts 未安装，语音功能不可用")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='../templates')
app.config['JSON_AS_ASCII'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'qa-assistant-secret-key-2024')

# TTS 配置
TTS_VOICE = "zh-CN-YunyangNeural"  # 默认使用云扬（沉稳男声）

# 缓存问答对
qa_pairs_cache = None


def get_qa_pairs():
    """获取问答对缓存"""
    global qa_pairs_cache
    if qa_pairs_cache is None:
        qa_pairs_cache = load_answers_from_excel()
    return qa_pairs_cache


async def synthesize_speech_async(text: str, voice: str = TTS_VOICE) -> bytes:
    """异步合成语音"""
    if not EDGE_TTS_AVAILABLE:
        raise Exception("edge-tts 未安装")

    communicate = edge_tts.Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data


def synthesize_speech(text: str, voice: str = TTS_VOICE) -> bytes:
    """同步合成语音"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_data = loop.run_until_complete(synthesize_speech_async(text, voice))
        loop.close()
        return audio_data
    except Exception as e:
        logger.error(f"语音合成失败: {e}")
        raise


@app.route('/')
def index():
    """渲染主页，需先登录"""
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """处理登录请求"""
    if request.method == 'GET':
        return render_template('login.html')

    password = request.form.get('password', '')

    if password == '香连止痢丸':
        session['logged_in'] = True
        return render_template('index.html')
    else:
        return render_template('login.html', error='口令错误，请重新输入')


@app.route('/api/questions', methods=['GET'])
def get_questions():
    """获取快捷问题列表（分页）"""
    page = request.args.get('page', 0, type=int)
    page_size = request.args.get('page_size', 5, type=int)

    questions, total = get_paginated_questions(page, page_size)

    return jsonify({
        'success': True,
        'questions': questions,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size
    })


@app.route('/api/recommend', methods=['POST'])
def recommend_questions():
    """智能推荐相关问题"""
    data = request.get_json()
    user_question = data.get('question', '')

    if not user_question:
        return jsonify({'success': False, 'error': '问题不能为空'})

    recommended = get_recommended_questions(user_question, 5)

    return jsonify({
        'success': True,
        'recommendations': recommended
    })


@app.route('/api/ask', methods=['POST'])
def ask_question():
    """处理用户提问"""
    data = request.get_json()
    user_question = data.get('question', '')

    if not user_question:
        return jsonify({'success': False, 'error': '问题不能为空'})

    try:
        # 只从知识库中查找匹配（离线版本不使用 LLM）
        qa_pairs = get_qa_pairs()
        matched_answer = find_best_match(user_question, qa_pairs)

        if matched_answer:
            answer = matched_answer
            source = 'knowledge_base'
        else:
            answer = "抱歉，知识库中没有找到相关答案。"
            source = 'none'

        return jsonify({
            'success': True,
            'answer': answer,
            'source': source,
            'question': user_question
        })

    except Exception as e:
        logger.error(f"处理问题时出错: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/tts/url', methods=['POST'])
def text_to_speech_url():
    """获取语音 URL（返回 base64 数据）"""
    data = request.get_json()
    text = data.get('text', '')

    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'})

    try:
        if not EDGE_TTS_AVAILABLE:
            return jsonify({'success': False, 'error': '语音功能不可用，请安装 edge-tts'})

        # 使用 Edge-TTS 合成语音
        audio_data = synthesize_speech(text, TTS_VOICE)
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        return jsonify({
            'success': True,
            'audio_url': f"data:audio/mp3;base64,{audio_base64}",
            'audio_size': len(audio_data)
        })

    except Exception as e:
        logger.error(f"TTS 处理时出错: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'message': '服务正常运行（离线模式）',
        'tts_available': EDGE_TTS_AVAILABLE,
        'tts_voice': TTS_VOICE if EDGE_TTS_AVAILABLE else None
    })


def init_app():
    """初始化应用"""
    logger.info("正在初始化问答助手（离线版本）...")
    init_knowledge_base()
    logger.info(f"语音合成: {'已启用' if EDGE_TTS_AVAILABLE else '未启用'} (使用 {TTS_VOICE})")
    logger.info("初始化完成")


if __name__ == '__main__':
    init_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
