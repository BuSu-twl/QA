"""
基于知识库的问答助手 - Flask 后端
"""
import os
import logging
from flask import Flask, render_template, request, jsonify, send_file, session, redirect
from io import BytesIO
import base64

from coze_coding_dev_sdk import LLMClient, TTSClient
from coze_coding_utils.runtime_ctx.context import new_context

from knowledge_base import (
    load_answers_from_excel,
    get_paginated_questions,
    get_recommended_questions,
    find_best_match,
    init_knowledge_base
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'qa-assistant-secret-key-2024')

# 初始化上下文
llm_ctx = new_context(method="llm.invoke")
tts_ctx = new_context(method="tts.synthesize")

# 初始化客户端
llm_client = LLMClient(ctx=llm_ctx)
tts_client = TTSClient(ctx=tts_ctx)

# 缓存问答对
qa_pairs_cache = None


def get_qa_pairs():
    """获取问答对缓存"""
    global qa_pairs_cache
    if qa_pairs_cache is None:
        qa_pairs_cache = load_answers_from_excel()
    return qa_pairs_cache


@app.route('/')
def index():
    """渲染主页，需先登录"""
    # 检查 session 中是否有登录标记
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """处理登录请求"""
    # GET 请求显示登录页
    if request.method == 'GET':
        return render_template('login.html')
    
    # POST 请求处理登录
    password = request.form.get('password', '')
    
    if password == '香连止痢丸':
        session['logged_in'] = True
        return render_template('index.html')  # 直接返回聊天页面
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
        # 先从知识库中查找匹配
        qa_pairs = get_qa_pairs()
        matched_answer = find_best_match(user_question, qa_pairs)

        if matched_answer:
            # 知识库有答案
            answer = matched_answer
            source = 'knowledge_base'
        else:
            # 使用 LLM 生成答案
            system_prompt = """你是一个专业的问答助手，基于给定的知识库回答用户问题。
请用简洁、清晰的语言回答。如果知识库中没有相关信息，请礼貌地告知用户。
回答时注意：
1. 保持专业和友好的语气
2. 回答要准确、简洁
3. 如果不确定，请明确告知"""

            from langchain_core.messages import SystemMessage, HumanMessage

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"用户问题：{user_question}\n\n请根据知识库内容回答这个问题。")
            ]

            response = llm_client.invoke(messages=messages, temperature=0.7)
            answer = response.content if isinstance(response.content, str) else str(response.content)
            source = 'llm'

        return jsonify({
            'success': True,
            'answer': answer,
            'source': source,
            'question': user_question
        })

    except Exception as e:
        logger.error(f"处理问题时出错: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    """将文本转换为语音"""
    data = request.get_json()
    text = data.get('text', '')

    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'})

    try:
        # 调用 TTS 服务
        audio_url, audio_size = tts_client.synthesize(
            uid="qa_assistant",
            text=text,
            speaker="zh_male_m191_uranus_bigtts",
            audio_format="mp3",
            sample_rate=24000
        )

        # 下载音频文件
        import requests as http
        audio_response = http.get(audio_url)

        if audio_response.status_code == 200:
            # 将音频转为 base64
            audio_base64 = base64.b64encode(audio_response.content).decode('utf-8')

            return jsonify({
                'success': True,
                'audio_url': f"data:audio/mp3;base64,{audio_base64}",
                'audio_size': audio_size
            })
        else:
            return jsonify({'success': False, 'error': '音频下载失败'})

    except Exception as e:
        logger.error(f"TTS 处理时出错: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/tts/url', methods=['POST'])
def text_to_speech_url():
    """获取语音 URL（返回 base64 数据）"""
    data = request.get_json()
    text = data.get('text', '')

    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'})

    try:
        audio_url, audio_size = tts_client.synthesize(
            uid="qa_assistant",
            text=text,
            speaker="zh_male_m191_uranus_bigtts",
            audio_format="mp3",
            sample_rate=24000
        )
        
        # 下载音频文件并转为 base64
        import requests as http
        audio_response = http.get(audio_url)
        
        if audio_response.status_code == 200:
            audio_base64 = base64.b64encode(audio_response.content).decode('utf-8')
            return jsonify({
                'success': True,
                'audio_url': f"data:audio/mp3;base64,{audio_base64}",
                'audio_size': audio_size
            })
        else:
            return jsonify({'success': False, 'error': '音频下载失败'})

    except Exception as e:
        logger.error(f"TTS 处理时出错: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({'status': 'ok', 'message': '服务正常运行'})


def init_app():
    """初始化应用"""
    logger.info("正在初始化问答助手...")
    init_knowledge_base()
    logger.info("初始化完成")


if __name__ == '__main__':
    init_app()
    # 使用 5000 端口
    app.run(host='0.0.0.0', port=5000, debug=True)
