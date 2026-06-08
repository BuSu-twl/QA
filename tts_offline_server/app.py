"""
基于知识库的问答助手 - Flask 后端（离线版本）
使用 Edge-TTS 离线语音合成
"""
import os
import sys

# ===== PyInstaller 兼容：修复 pyexpat DLL 加载失败 =====
# Anaconda 环境下 pyexpat.pyd 依赖 libexpat.dll 等外部 DLL
# PyInstaller 可能没有正确收集这些依赖
if getattr(sys, 'frozen', False):
    # 添加 DLL 搜索路径：
    # 1. _MEIPASS（打包内部目录）
    # 2. exe 同级目录（COLLECT 模式下 DLL 放在这里）
    # 3. 原始 Python 环境的 DLLs 目录（作为最终回退）
    possible_dll_dirs = [
        os.path.join(sys._MEIPASS, 'DLLs'),
        os.path.join(sys._MEIPASS),
        os.path.dirname(sys.executable),  # exe 同级目录
    ]
    # 添加原始 Python 环境的 DLL 目录
    try:
        import _ctypes
        if hasattr(_ctypes, '__file__'):
            py_dll_dir = os.path.dirname(_ctypes.__file__)
            if py_dll_dir not in possible_dll_dirs:
                possible_dll_dirs.append(py_dll_dir)
            # Anaconda: DLLs 在 Python 根目录下
            conda_root = os.path.dirname(py_dll_dir)
            possible_dll_dirs.append(os.path.join(conda_root, 'DLLs'))
            possible_dll_dirs.append(os.path.join(conda_root, 'Library', 'bin'))
            possible_dll_dirs.append(conda_root)
    except Exception:
        pass

    for dll_dir in possible_dll_dirs:
        if os.path.isdir(dll_dir):
            if dll_dir not in os.environ.get('PATH', ''):
                os.environ['PATH'] = dll_dir + os.pathsep + os.environ.get('PATH', '')
            if hasattr(os, 'add_dll_directory'):
                try:
                    os.add_dll_directory(dll_dir)
                except (OSError, FileNotFoundError):
                    pass

import logging
import asyncio
from flask import Flask, render_template, request, jsonify, session, redirect, send_file
import base64

# ===== PyInstaller 打包路径兼容 =====
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后，_MEIPASS 是解压临时目录
    _INTERNAL_DIR = sys._MEIPASS
    # exe 所在目录（用户可读写，放置 data/templates 等外部文件）
    _EXTERNAL_DIR = os.path.dirname(sys.executable)
else:
    _INTERNAL_DIR = os.path.dirname(os.path.abspath(__file__))
    _EXTERNAL_DIR = _INTERNAL_DIR


def _resolve_path(relative_path):
    """
    解析资源文件路径：
    优先从 exe 同级目录（外部）查找，找不到再从打包内部查找。
    这样用户可以把 data/templates 放在 exe 旁边，方便修改。
    """
    # 1. 先看 exe 同级目录
    external = os.path.join(_EXTERNAL_DIR, relative_path)
    if os.path.exists(external):
        return external
    # 2. 再看打包内部
    internal = os.path.join(_INTERNAL_DIR, relative_path)
    return internal


# 获取当前目录（兼容 PyInstaller）
BASE_DIR = _EXTERNAL_DIR

# 设置 Edge-TTS 缓存目录（使用本地 models 文件夹）
MODELS_DIR = os.path.join(BASE_DIR, 'models')
if not os.environ.get('EDGE_TTS_CACHE_DIR'):
    os.environ['EDGE_TTS_CACHE_DIR'] = MODELS_DIR

# 添加路径，以便导入 knowledge_base
# _INTERNAL_DIR 优先，确保导入本目录下的 knowledge_base 而非其他目录的旧版
sys.path.insert(0, _INTERNAL_DIR)
sys.path.append(_EXTERNAL_DIR)

from knowledge_base import (
    load_answers_from_excel,
    get_paginated_questions,
    get_recommended_questions,
    find_best_match,
    init_knowledge_base,
    reload_knowledge_base
)

# TTS 引擎和线程锁
import threading
_tts_lock = threading.Lock()

# 尝试导入 pyttsx3（Windows 离线语音，完全不需要网络）
# 注意：不在模块级别初始化引擎，避免 PyInstaller 打包后启动卡住
PYTTSX3_AVAILABLE = False
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
    print("Pyttsx3 已加载（离线模式）")
except ImportError:
    print("Pyttsx3 未安装")

# 尝试导入 edge-tts（在线语音）
EDGE_TTS_AVAILABLE = False
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
    print("Edge-TTS 已加载（需要联网）")
except ImportError:
    print("Edge-TTS 未安装")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder=_resolve_path('templates'), static_folder=_resolve_path('static'))
app.config['JSON_AS_ASCII'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'qa-assistant-secret-key-2024')

# TTS 配置
TTS_VOICE = "zh-CN-YunyangNeural"  # 默认使用云扬（沉稳男声）

# 离线 TTS 配置
AUDIO_DIR = os.path.join(BASE_DIR, 'audio')


def get_text_hash(text: str) -> str:
    """获取文本的哈希值作为文件名"""
    import hashlib
    # 移除空格和标点，生成短哈希
    clean_text = ''.join(c for c in text if c not in ' \n\t.,。，')
    return hashlib.md5(clean_text.encode('utf-8')).hexdigest()[:12]


def get_offline_audio(text: str) -> bytes:
    """从本地 audio 目录获取预生成的音频"""
    text_hash = get_text_hash(text)
    audio_file = os.path.join(AUDIO_DIR, f"{text_hash}.mp3")

    if os.path.exists(audio_file):
        try:
            with open(audio_file, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"读取离线音频失败: {e}")

    return None


def synthesize_with_pyttsx3(text: str) -> bytes:
    """使用 Pyttsx3 合成语音（离线模式，Windows SAPI5）

    每次调用创建新引擎，避免 SAPI5 COM 对象线程安全问题。
    使用线程锁保证同一时间只有一个 TTS 调用。
    """
    if not PYTTSX3_AVAILABLE:
        raise Exception("Pyttsx3 不可用")

    # 加锁，防止并发调用导致 SAPI5 COM 对象冲突
    if not _tts_lock.acquire(timeout=15):
        raise Exception("TTS 引擎正忙，请稍后重试")

    temp_file = os.path.join(BASE_DIR, 'temp_tts.mp3')

    try:
        # 每次创建新引擎，避免 COM 对象跨线程/重用问题
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)  # 语速

        # 尝试设置中文男声
        voices = engine.getProperty('voices')
        male_voice_found = False
        # 优先查找 Kangkang（Windows 自带中文男声）
        for voice in voices:
            voice_id = voice.id.lower() if voice.id else ''
            voice_name = voice.name.lower() if voice.name else ''
            # 优先级: Kangkang > 其他男声 > 任何中文声音
            if 'kangkang' in voice_id or 'kangkang' in voice_name:
                engine.setProperty('voice', voice.id)
                male_voice_found = True
                logger.info(f"Pyttsx3 使用中文男声: {voice.name}")
                break
        if not male_voice_found:
            # 尝试查找其他中文男声标识
            for voice in voices:
                voice_id = voice.id.lower() if voice.id else ''
                voice_name = voice.name.lower() if voice.name else ''
                if ('zh' in voice_id or 'chinese' in voice_name or 'zh' in voice_name) and \
                   ('male' in voice_id or 'male' in voice_name or 'nan' in voice_id):
                    engine.setProperty('voice', voice.id)
                    male_voice_found = True
                    logger.info(f"Pyttsx3 使用中文男声: {voice.name}")
                    break
        if not male_voice_found:
            # 降级：使用任意中文声音
            for voice in voices:
                voice_id = voice.id.lower() if voice.id else ''
                voice_name = voice.name.lower() if voice.name else ''
                if 'zh' in voice_id or 'chinese' in voice_name or 'zh' in voice_name:
                    engine.setProperty('voice', voice.id)
                    logger.info(f"Pyttsx3 使用中文语音（未找到男声）: {voice.name}")
                    break

        # 合成到文件
        engine.save_to_file(text, temp_file)
        engine.runAndWait()

        # 清理引擎
        try:
            engine.stop()
            del engine
        except Exception:
            pass

        # 读取文件
        if not os.path.exists(temp_file):
            raise Exception("Pyttsx3 未能生成音频文件")

        with open(temp_file, 'rb') as f:
            audio_data = f.read()

        # 删除临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)

        return audio_data
    except Exception as e:
        logger.error(f"Pyttsx3 合成失败: {e}")
        # 删除可能存在的临时文件
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
        raise
    finally:
        _tts_lock.release()


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

    result = get_paginated_questions(page, page_size)
    questions = result.get('questions', [])
    total = result.get('total', 0)

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
        answer, matched_question = find_best_match(user_question)

        if answer:
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
    """获取语音 URL（返回 base64 数据）
    优先使用本地预生成音频，离线可用
    """
    data = request.get_json()
    text = data.get('text', '')

    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'})

    try:
        # 1. 优先从本地 audio 目录获取预生成的音频
        offline_audio = get_offline_audio(text)
        if offline_audio:
            audio_base64 = base64.b64encode(offline_audio).decode('utf-8')
            return jsonify({
                'success': True,
                'audio_url': f"data:audio/mp3;base64,{audio_base64}",
                'audio_size': len(offline_audio),
                'source': 'offline'
            })

        # 2. 尝试 Edge-TTS（云扬男声，需要联网）
        if EDGE_TTS_AVAILABLE:
            try:
                audio_data = synthesize_speech(text, TTS_VOICE)
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                logger.info(f"Edge-TTS 合成成功 ({TTS_VOICE}): {len(audio_data)} 字节")
                return jsonify({
                    'success': True,
                    'audio_url': f"data:audio/mp3;base64,{audio_base64}",
                    'audio_size': len(audio_data),
                    'source': 'edge-tts'
                })
            except Exception as edge_error:
                logger.warning(f"Edge-TTS 合成失败: {edge_error}")

        # 3. Edge-TTS 不可用或失败，尝试 Pyttsx3（离线兜底，可能为女声）
        if PYTTSX3_AVAILABLE:
            try:
                audio_data = synthesize_with_pyttsx3(text)
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                logger.info(f"Pyttsx3 合成成功: {len(audio_data)} 字节")
                return jsonify({
                    'success': True,
                    'audio_url': f"data:audio/mp3;base64,{audio_base64}",
                    'audio_size': len(audio_data),
                    'source': 'pyttsx3'
                })
            except Exception as pyttsx3_error:
                logger.warning(f"Pyttsx3 合成失败: {pyttsx3_error}")

        # 4. 全部失败
        return jsonify({'success': False, 'error': '语音功能不可用'})

    except Exception as e:
        logger.error(f"TTS 处理时出错: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/favicon.ico')
def favicon():
    """Favicon 路由"""
    favicon_path = os.path.join(_resolve_path('static'), 'avatar_open.png')
    if os.path.exists(favicon_path):
        return send_file(favicon_path, mimetype='image/png')
    return '', 404


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    # 诊断路径信息
    from knowledge_base import DATA_DIR, QUESTION_FILE, ANSWER_FILE
    data_exists = os.path.exists(DATA_DIR)
    q_exists = os.path.exists(QUESTION_FILE)
    a_exists = os.path.exists(ANSWER_FILE)

    return jsonify({
        'status': 'ok',
        'message': '服务正常运行（离线模式）',
        'tts_available': EDGE_TTS_AVAILABLE,
        'tts_voice': TTS_VOICE if EDGE_TTS_AVAILABLE else None,
        'debug': {
            'internal_dir': _INTERNAL_DIR,
            'external_dir': _EXTERNAL_DIR,
            'data_dir': DATA_DIR,
            'data_exists': data_exists,
            'question_file': QUESTION_FILE,
            'question_exists': q_exists,
            'answer_file': ANSWER_FILE,
            'answer_exists': a_exists,
        }
    })


@app.route('/api/reload', methods=['POST'])
def reload_kb():
    """重新加载知识库（修改 xlsx 后调用）"""
    try:
        success = reload_knowledge_base()
        if success:
            return jsonify({'success': True, 'message': '知识库已重新加载'})
        else:
            return jsonify({'success': False, 'message': '知识库重新加载失败，请检查数据文件'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'重新加载出错: {str(e)}'}), 500


@app.route('/api/debug/kb', methods=['GET'])
def debug_knowledge_base():
    """调试接口：查看知识库加载状态和匹配测试"""
    from knowledge_base import QUESTIONS, QA_PAIRS, QA_DIRECT, get_question_by_id, find_best_match
    test_q = request.args.get('q', '')
    result = {
        'questions_count': len(QUESTIONS),
        'qa_pairs_count': len(QA_PAIRS),
        'qa_direct_count': len(QA_DIRECT),
        'questions_sample': [],
        'qa_direct_sample': [],
    }
    for i, q in enumerate(QUESTIONS[:5]):
        result['questions_sample'].append({'index': i + 1, 'text': q})
    for qa in QA_DIRECT[:5]:
        result['qa_direct_sample'].append({
            'question': qa['question'],
            'answer_preview': qa['answer'][:80] if qa['answer'] else None,
            'source': qa.get('source', 'unknown'),
        })
    # 检查 QA_PAIRS 的 ID 映射情况
    id_mapping_ok = 0
    id_mapping_fail = 0
    for qa in QA_PAIRS:
        if get_question_by_id(qa['question_id']):
            id_mapping_ok += 1
        else:
            id_mapping_fail += 1
    result['id_mapping'] = {'ok': id_mapping_ok, 'fail': id_mapping_fail}
    # QA_PAIRS 样本
    result['qa_pairs_sample'] = []
    for qa in QA_PAIRS[:5]:
        q_text = get_question_by_id(qa['question_id'])
        result['qa_pairs_sample'].append({
            'question_id': str(qa['question_id']),
            'question_text': q_text,
            'answer_preview': qa['answer'][:50] if qa['answer'] else None,
        })
    if test_q:
        answer, matched = find_best_match(test_q)
        result['test_match'] = {
            'input': test_q,
            'matched_question': matched,
            'answer': answer[:100] if answer else None,
        }
    return jsonify(result)


def init_app():
    """初始化应用"""
    logger.info("正在初始化问答助手（离线版本）...")
    init_knowledge_base()

    # pyttsx3 不再预先初始化引擎，改为每次调用时创建新引擎
    # 这样可以避免 SAPI5 COM 对象的线程安全问题
    if PYTTSX3_AVAILABLE:
        logger.info("Pyttsx3 语音已就绪（按需创建引擎）")

    # 清晰显示 TTS 引擎状态
    if EDGE_TTS_AVAILABLE:
        logger.info(f"语音合成: Edge-TTS ({TTS_VOICE} 沉稳男声)")
    elif PYTTSX3_AVAILABLE:
        logger.info("语音合成: Pyttsx3 (SAPI5，Windows系统语音，可能为女声)")
        logger.info("  提示: 安装 edge-tts 可使用高质量男声: pip install edge-tts")
    else:
        logger.info("语音合成: 未启用（请安装 edge-tts 或 pyttsx3）")
    logger.info("初始化完成")


def main():
    """主启动入口"""
    init_app()
    port = int(os.environ.get('DEPLOY_RUN_PORT', 5000))

    # 自动打开浏览器
    import webbrowser
    import threading

    def open_browser():
        import time
        time.sleep(2)
        webbrowser.open(f'http://localhost:{port}')

    threading.Thread(target=open_browser, daemon=True).start()

    print("=" * 50)
    print("  Medical QA Assistant")
    print("=" * 50)
    print(f"  URL: http://localhost:{port}")
    print("  Press Ctrl+C to stop")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    main()
