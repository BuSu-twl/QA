"""
知识库处理模块（离线版本）
直接从本地 Excel 文件读取数据，无需网络
"""
import os
import sys
import re

# ===== PyInstaller 兼容：确保 XML 解析器可用 =====
# openpyxl 依赖 xml.etree.ElementTree → pyexpat
# PyInstaller 打包后 pyexpat DLL 可能加载失败，这里做兜底处理
try:
    import pyexpat  # 测试是否能正常加载
except ImportError:
    # pyexpat 不可用，使用纯 Python 解析器替代
    import xml.etree.ElementTree
    # 强制使用纯 Python 解析器
    import xml.parsers
    import io

    class _SimpleExpatParser:
        """纯 Python XML 解析器替代（用于 PyInstaller 打包后 pyexpat 不可用的情况）"""
        pass

    # 设置 xml.parsers.expat 模块的兼容标记
    if not hasattr(xml.parsers, 'expat') or xml.parsers.expat is None:
        # 尝试 import xml.parsers.expat 的纯 Python 版本
        try:
            from xml.parsers import expat as _expat_mod
        except ImportError:
            # 创建一个兼容模块
            import types
            _expat_mod = types.ModuleType('xml.parsers.expat')
            xml.parsers.expat = _expat_mod
            sys.modules['xml.parsers.expat'] = _expat_mod

import openpyxl
from typing import List, Dict, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== PyInstaller 打包路径兼容 =====
if getattr(sys, 'frozen', False):
    _INTERNAL_DIR = sys._MEIPASS
    _EXTERNAL_DIR = os.path.dirname(sys.executable)
else:
    _INTERNAL_DIR = os.path.dirname(os.path.abspath(__file__))
    _EXTERNAL_DIR = _INTERNAL_DIR


def _resolve_path(relative_path):
    """解析资源文件路径：优先外部目录，再内部目录"""
    external = os.path.join(_EXTERNAL_DIR, relative_path)
    if os.path.exists(external):
        return external
    internal = os.path.join(_INTERNAL_DIR, relative_path)
    return internal


# 本地文件路径（兼容 PyInstaller）
DATA_DIR = _resolve_path('data')
ANSWER_FILE = os.path.join(DATA_DIR, 'answer.xlsx')
QUESTION_FILE = os.path.join(DATA_DIR, 'question.xlsx')


def load_questions_from_excel() -> List[str]:
    """从问题表加载所有问题"""
    questions = []

    try:
        wb = openpyxl.load_workbook(QUESTION_FILE)
        ws = wb.active

        # 遍历所有行，获取第二列的问题内容
        # 问题表结构：A列=问题序号，B列=问题内容
        for row in ws.iter_rows(min_row=2, values_only=True):
            if len(row) >= 2 and row[1] and isinstance(row[1], str):
                question = row[1].strip()
                if question:
                    questions.append(question)

        wb.close()
        logger.info(f"加载了 {len(questions)} 个问题")
        return questions
    except Exception as e:
        logger.error(f"读取问题表失败: {e}")
        return []


def load_answers_from_excel() -> List[Dict[str, str]]:
    """从答案表加载问题和答案
    答案表结构可能有以下两种情况：
    1. 标准格式：A列=问题序号（如"问题1"），B列=答案内容，第一行是表头
    2. 数据头格式：A列第一行就是"问题1答案"，没有标准表头
    本函数自动检测并兼容两种格式
    """
    qa_pairs = []

    try:
        wb = openpyxl.load_workbook(ANSWER_FILE)
        ws = wb.active

        # 先读取第一行，判断是否是标准表头
        first_row = None
        for row in ws.iter_rows(min_row=1, max_row=1, values_only=True):
            first_row = row
            break

        # 判断第一行是否是数据行（包含"问题"或数字ID）
        start_row = 2  # 默认跳过表头
        if first_row and len(first_row) >= 2 and first_row[1] and isinstance(first_row[1], str):
            first_col = str(first_row[0]).strip() if first_row[0] else ''
            # 如果第一行A列包含"问题"且B列有实际内容，说明第一行就是数据
            if ('问题' in first_col or re.match(r'^\d+$', first_col)) and len(first_row[1].strip()) > 5:
                # 第一行是数据，从第一行开始读
                start_row = 1
                qa_pairs.append({
                    'question_id': first_row[0],
                    'answer': first_row[1].strip()
                })

        # 从第二行（或第一行）开始读取数据
        for row in ws.iter_rows(min_row=start_row + 1, values_only=True):
            if len(row) >= 2 and row[1] and isinstance(row[1], str):
                answer = row[1].strip()
                if answer:
                    qa_pairs.append({
                        'question_id': row[0],
                        'answer': answer
                    })

        wb.close()
        logger.info(f"加载了 {len(qa_pairs)} 个问答对")
        return qa_pairs
    except Exception as e:
        logger.error(f"读取答案表失败: {e}")
        return []


def _normalize_text(text: str) -> str:
    """标准化文本用于模糊匹配：统一标点、去空格、转小写，只保留有意义字符"""
    text = text.strip().lower()
    # 统一中文标点为英文标点
    for old, new in [('？','?'),('！','!'),('，',','),('。','.'),('：',':'),('；',';'),
                     ('"','"'),('"','"'),('（','('),('）',')'),('【','['),('】',']')]:
        text = text.replace(old, new)
    # 去掉所有标点和空格，只保留字母数字和中文
    text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
    return text


def _extract_question_index(question_id) -> Optional[int]:
    """从 question_id 中提取问题序号（0-based 索引）
    支持的格式：
    - "问题1", "问题1答案", "1", "1答案"
    - 数字类型: 1, 2, 3...
    """
    qid_str = str(question_id).strip()
    # 移除常见后缀
    qid_str = qid_str.replace('答案', '').replace('问题', '').strip()
    # 提取数字
    nums = re.findall(r'\d+', qid_str)
    if nums:
        return int(nums[0]) - 1  # 转为 0-based 索引
    return None


# 全局变量存储知识库数据
QUESTIONS: List[str] = []
QA_PAIRS: List[Dict[str, str]] = []
# 直接的 问答对（question_text → answer），更可靠的匹配方式
QA_DIRECT: List[Dict[str, str]] = []


def _build_qa_direct():
    """构建直接的问答映射：将每个问题和对应答案配对
    策略：
    1. 如果答案表的 question_id 能映射到问题表，使用问题文本
    2. 如果无法映射，按位置顺序配对（假设问题和答案一一对应）
    """
    global QA_DIRECT
    QA_DIRECT = []

    for qa in QA_PAIRS:
        question_text = get_question_by_id(qa['question_id'])
        if question_text:
            QA_DIRECT.append({
                'question': question_text,
                'answer': qa['answer'],
                'source': 'id_match'
            })

    # 如果通过 ID 映射的数量不对，尝试按位置配对
    if len(QA_DIRECT) != len(QA_PAIRS) and len(QUESTIONS) == len(QA_PAIRS):
        logger.info(f"ID映射不完整({len(QA_DIRECT)}/{len(QA_PAIRS)})，尝试按位置配对")
        QA_DIRECT = []
        for i, qa in enumerate(QA_PAIRS):
            if i < len(QUESTIONS):
                QA_DIRECT.append({
                    'question': QUESTIONS[i],
                    'answer': qa['answer'],
                    'source': 'positional'
                })

    # 如果问题比答案多，剩余问题没有答案
    if not QA_DIRECT and QUESTIONS and QA_PAIRS:
        logger.warning("无法建立问答映射，使用顺序配对")
        for i in range(min(len(QUESTIONS), len(QA_PAIRS))):
            QA_DIRECT.append({
                'question': QUESTIONS[i],
                'answer': QA_PAIRS[i]['answer'],
                'source': 'fallback'
            })

    logger.info(f"构建了 {len(QA_DIRECT)} 个直接问答对")


def get_question_by_id(question_id) -> Optional[str]:
    """根据问题ID获取问题内容"""
    try:
        idx = _extract_question_index(question_id)
        if idx is not None and 0 <= idx < len(QUESTIONS):
            return QUESTIONS[idx]
    except Exception:
        pass
    return None


def find_answer_by_question(question: str) -> Tuple[Optional[str], Optional[str]]:
    """
    根据问题查找答案（多级模糊匹配）
    返回: (答案, 匹配的问题)
    优先使用 QA_DIRECT（直接问答对），更可靠
    """
    # 优先使用 QA_DIRECT 匹配
    if QA_DIRECT:
        return _match_from_qa_direct(question)

    # 降级：使用 QA_PAIRS + get_question_by_id
    if QA_PAIRS:
        return _match_from_qa_pairs(question)

    return None, None


def _match_from_qa_direct(question: str) -> Tuple[Optional[str], Optional[str]]:
    """从 QA_DIRECT 中匹配（推荐路径，更可靠）"""
    question_norm = _normalize_text(question)

    # 1. 精确匹配
    for qa in QA_DIRECT:
        if _normalize_text(qa['question']) == question_norm:
            return qa['answer'], qa['question']

    # 2. 子串匹配（标准化后互相包含）
    for qa in QA_DIRECT:
        stored_norm = _normalize_text(qa['question'])
        if question_norm in stored_norm or stored_norm in question_norm:
            return qa['answer'], qa['question']

    # 3. 核心词匹配：提取 3+ 字连续中文词段作为核心词
    #    如果用户问题的核心词出现在存储问题中，说明语义相关
    def _extract_key_terms(text, min_len=3):
        """提取 min_len 字及以上的连续中文词段作为核心词"""
        clean = re.sub(r'[^\u4e00-\u9fff]', '', text)
        terms = set()
        for length in range(min(len(clean), 8), min_len - 1, -1):
            for i in range(len(clean) - length + 1):
                terms.add(clean[i:i+length])
        return terms

    q_key_terms = _extract_key_terms(question_norm, 3)
    if q_key_terms:
        best_key_score = 0
        best_key_qa = None
        for qa in QA_DIRECT:
            s_key_terms = _extract_key_terms(_normalize_text(qa['question']), 3)
            overlap = q_key_terms & s_key_terms
            if not overlap:
                continue
            max_overlap_len = max(len(t) for t in overlap)
            score = len(overlap) / max(len(q_key_terms), 1)
            if max_overlap_len >= 3:
                score += 0.3
            if score > best_key_score:
                best_key_score = score
                best_key_qa = qa

        if best_key_score >= 0.3 and best_key_qa:
            return best_key_qa['answer'], best_key_qa['question']

    # 4. 关键 2 字词段匹配：提取有意义的 2 字词段，计算重叠度
    #    用于处理用户使用药名（如"香连止痢丸"）替代"该处方"的情况
    _STOP_CHARS = set('的是了在吗呢吧啊呀哦哈嗯这那也还又被把让给向从到和不与及等都')
    _STOP_BIGRAMS = {'什么', '怎么', '如何', '可以', '是否', '能否', '为什么',
                     '哪些', '没有', '就是', '不是', '还是', '或者', '而且',
                     '因为', '所以', '如果', '虽然', '但是', '以及', '以后'}

    def _extract_meaningful_bigrams(text):
        """提取有意义的 2 字词段，过滤停用字和常见虚词"""
        clean = re.sub(r'[^\u4e00-\u9fff]', '', text)
        bigrams = set()
        for i in range(len(clean) - 1):
            bigram = clean[i:i+2]
            # 过滤停用字组合
            if bigram[0] in _STOP_CHARS and bigram[1] in _STOP_CHARS:
                continue
            # 过滤常见虚词
            if bigram in _STOP_BIGRAMS:
                continue
            bigrams.add(bigram)
        return bigrams

    q_bigrams = _extract_meaningful_bigrams(question_norm)
    if q_bigrams:
        best_bi_score = 0
        best_bi_qa = None
        for qa in QA_DIRECT:
            s_bigrams = _extract_meaningful_bigrams(_normalize_text(qa['question']))
            overlap = q_bigrams & s_bigrams
            if not overlap:
                continue
            score = len(overlap) / max(len(q_bigrams), 1)
            if score > best_bi_score:
                best_bi_score = score
                best_bi_qa = qa

        if best_bi_score >= 0.15 and best_bi_qa:
            return best_bi_qa['answer'], best_bi_qa['question']

    # 5. N-gram 交集匹配（兜底策略）
    def _tokenize(text):
        clean = re.sub(r'[？?！!。，,、：:；;（）()《》\s]', '', text)
        tokens = set()
        for length in [2, 3, 4]:
            for i in range(len(clean) - length + 1):
                tokens.add(clean[i:i+length])
        return tokens

    q_tokens = _tokenize(question_norm)
    if q_tokens:
        best_kw_score = 0
        best_kw_qa = None
        for qa in QA_DIRECT:
            s_tokens = _tokenize(_normalize_text(qa['question']))
            if not s_tokens:
                continue
            overlap_count = len(q_tokens & s_tokens)
            score = overlap_count / max(len(q_tokens), 1)
            if score > best_kw_score:
                best_kw_score = score
                best_kw_qa = qa

        if best_kw_score >= 0.25 and best_kw_qa:
            return best_kw_qa['answer'], best_kw_qa['question']

    return None, None

    return None, None


def _match_from_qa_pairs(question: str) -> Tuple[Optional[str], Optional[str]]:
    """从 QA_PAIRS 中匹配（降级路径）"""
    question_norm = _normalize_text(question)

    # 1. 精确匹配
    for qa in QA_PAIRS:
        stored_question = get_question_by_id(qa['question_id'])
        if stored_question and _normalize_text(stored_question) == question_norm:
            return qa['answer'], stored_question

    # 2. 子串匹配
    for qa in QA_PAIRS:
        stored_question = get_question_by_id(qa['question_id'])
        if not stored_question:
            continue
        stored_norm = _normalize_text(stored_question)
        if question_norm in stored_norm or stored_norm in question_norm:
            return qa['answer'], stored_question

    # 3. 关键词匹配
    best_score = 0
    best_qa = None
    best_stored = None
    for qa in QA_PAIRS:
        stored_question = get_question_by_id(qa['question_id'])
        if not stored_question:
            continue
        stored_norm = _normalize_text(stored_question)
        common = sum(1 for c in question_norm if c in stored_norm)
        score = common / max(len(question_norm), 1)
        if score > best_score:
            best_score = score
            best_qa = qa
            best_stored = stored_question

    if best_score >= 0.4 and best_qa:
        return best_qa['answer'], best_stored

    return None, None


def find_similar_questions(question: str, exclude: str = None, limit: int = 5) -> List[str]:
    """
    查找相似问题
    exclude: 要排除的问题（通常是当前问题）
    limit: 返回数量限制
    """
    question = question.strip().lower()
    similar = []

    # 提取关键词
    keywords = extract_keywords(question)

    for q in QUESTIONS:
        if exclude and (q.lower() in exclude.lower() or exclude.lower() in q.lower()):
            continue

        q_lower = q.lower()
        score = 0

        # 关键词匹配
        q_keywords = extract_keywords(q_lower)
        common_keywords = set(keywords) & set(q_keywords)
        score += len(common_keywords) * 3

        # 子串匹配
        if question in q_lower or q_lower in question:
            score += 5

        # 核心词匹配
        core_common = [w for w in common_keywords if len(w) > 1]
        if len(core_common) >= 1:
            score += 5

        # 关键词类别匹配
        category_keywords = ['如何', '怎么', '什么', '为什么', '哪里', '哪个', '多少',
                           '适用', '组成', '用法', '用量', '注意', '事项', '处方', '服用']
        for kw in category_keywords:
            if kw in question and kw in q_lower:
                score += 3

        if score > 0:
            similar.append((q, score))

    # 按分数排序
    similar.sort(key=lambda x: x[1], reverse=True)
    return [q for q, _ in similar[:limit]]


def extract_keywords(text: str) -> List[str]:
    """提取关键词（简单实现）"""
    # 去掉常见停用词
    stop_words = {'的', '了', '是', '在', '有', '和', '与', '及', '等', '都',
                  '也', '还', '又', '被', '把', '让', '给', '向', '从', '到',
                  '这', '那', '哪', '什么', '怎么', '如何', '为什么', '吗', '呢',
                  '啊', '吧', '嘛', '呀', '哦', '哈', '嗯'}
    words = []
    # 简单分词：按标点和空格分割，然后提取2-4字子串
    segments = re.split(r'[，。、？？！！；：\s,.;:!?]+', text)
    for seg in segments:
        seg = seg.strip()
        if not seg or seg in stop_words:
            continue
        if len(seg) <= 4:
            words.append(seg)
        else:
            # 对长文本提取2-3字关键词
            for length in [2, 3]:
                for i in range(len(seg) - length + 1):
                    w = seg[i:i+length]
                    if w not in stop_words:
                        words.append(w)
    return words


def reload_knowledge_base():
    """重新加载知识库（修改 xlsx 文件后调用）"""
    global QUESTIONS, QA_PAIRS, QA_DIRECT
    old_q, old_a = len(QUESTIONS), len(QA_PAIRS)

    QUESTIONS = load_questions_from_excel()
    QA_PAIRS = load_answers_from_excel()
    _build_qa_direct()

    logger.info(f"知识库已重新加载: {old_q}->{len(QUESTIONS)} 个问题, {old_a}->{len(QA_PAIRS)} 个问答对, {len(QA_DIRECT)} 个直接映射")
    return len(QUESTIONS) > 0 or len(QA_PAIRS) > 0


def init_knowledge_base():
    """初始化知识库"""
    global QUESTIONS, QA_PAIRS, QA_DIRECT

    logger.info("正在初始化知识库...")

    # 加载数据
    QUESTIONS = load_questions_from_excel()
    QA_PAIRS = load_answers_from_excel()
    _build_qa_direct()

    logger.info(f"知识库初始化完成: {len(QUESTIONS)} 个问题, {len(QA_PAIRS)} 个问答对, {len(QA_DIRECT)} 个直接映射")
    return len(QUESTIONS) > 0 or len(QA_PAIRS) > 0


def find_best_match(question: str) -> Tuple[Optional[str], Optional[str]]:
    """查找最佳匹配的问题和答案"""
    return find_answer_by_question(question)


def get_recommended_questions(question: str, limit: int = 5) -> List[str]:
    """获取推荐问题"""
    return find_similar_questions(question, exclude=question, limit=limit)


def get_all_questions(page: int = 0, page_size: int = 10) -> Dict:
    """分页获取所有问题"""
    total = len(QUESTIONS)
    start = page * page_size
    end = start + page_size

    return {
        'success': True,
        'questions': QUESTIONS[start:end],
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size
    }


def get_paginated_questions(page: int = 0, page_size: int = 10) -> Dict:
    """获取分页问题（兼容旧API）"""
    return get_all_questions(page, page_size)


def search_answer(question: str) -> Dict:
    """
    搜索答案
    返回: {'success': bool, 'answer': str, 'source': str, 'question': str}
    """
    # 首先精确匹配
    answer, matched_question = find_answer_by_question(question)

    if answer:
        return {
            'success': True,
            'answer': answer,
            'source': 'knowledge_base',
            'question': matched_question or question
        }

    # 如果知识库没有答案，返回提示
    return {
        'success': True,
        'answer': '抱歉，知识库中暂未收录该问题的答案。',
        'source': 'knowledge_base',
        'question': question
    }


def get_recommendations(question: str, limit: int = 5) -> List[str]:
    """获取推荐问题（别名）"""
    return get_recommended_questions(question, limit)
