"""
知识库处理模块（离线版本）
直接从本地 Excel 文件读取数据，无需网络
"""
import os
import sys
import re
import math
import json
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone

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
# RAG 知识块与检索索引
RAG_CHUNKS: List[Dict] = []
RAG_DOC_FREQ: Dict[str, int] = {}
RAG_AVG_DOC_LEN: float = 0.0
RAG_EMBEDDING_MODEL = None
RAG_EMBEDDING_BACKEND = 'disabled'
RAG_EMBEDDING_DIM = 0
RAG_EMBEDDING_CACHE_FILE = _resolve_path('data/embeddings.json')
RAG_EMBEDDING_MODEL_NAME = os.environ.get(
    'RAG_EMBEDDING_MODEL',
    'paraphrase-multilingual-MiniLM-L12-v2',
)
RAG_ENABLE_EMBEDDING = os.environ.get('RAG_ENABLE_EMBEDDING', '1').lower() not in {
    '0', 'false', 'no', 'off'
}
RAG_ENABLE_LLM = os.environ.get('RAG_ENABLE_LLM', '0').lower() in {
    '1', 'true', 'yes', 'on'
}

RAG_STOP_WORDS = {
    '的', '了', '是', '在', '有', '和', '与', '及', '等', '都', '也', '还',
    '又', '被', '把', '让', '给', '向', '从', '到', '这', '那', '哪', '什么',
    '怎么', '如何', '为什么', '吗', '呢', '啊', '吧', '嘛', '呀', '哦', '嗯',
    '香连止痢丸', '本品', '该药', '这个药'
}

RAG_QUERY_EXPANSIONS = [
    (('成分', '组成', '药材', '处方'), '处方组成 药材 由哪些药材组成'),
    (('功效', '作用', '效果', '有什么用'), '功效 清热燥湿 理气和胃 健脾止泻'),
    (('主治', '病症', '症状', '拉肚子', '腹泻', '痢疾'), '主治 病症 小儿急性腹泻 腹痛泄泻'),
    (('用法', '用量', '怎么吃', '服用', '吃几次', '几次', '几克', '一天', '一日', '每天'), '用法用量 口服 一次 一日'),
    (('饭前', '饭后', '空腹', '餐前', '餐后', '什么时候吃'), '饭前 饭后 服用'),
    (('注意', '禁忌', '不能吃', '忌口', '副作用', '高热', '脱水', '就医'), '注意事项 禁用 忌食 就医 寒湿 虚寒'),
    (('适用', '人群', '儿童', '小儿', '孩子', '谁能吃'), '适用人群 小儿 儿童 患儿'),
    (('停药', '提前停', '症状好转', '大便正常'), '停药 症状好转 大便正常'),
    (('感冒药', '感冒', '联用', '一起吃', '同时吃'), '感冒药 慎用 间隔 同服'),
    (('配伍', '方解', '君臣佐使', '分析'), '配伍特点 君 臣 佐 使'),
    (('香连丸', '区别', '不同', '一样吗'), '香连丸 区别 药味 功效 剂型'),
    (('剂型', '微丸', '肠溶', '包衣', '工艺'), '剂型 肠溶微丸 隔离衣 肠溶衣'),
]


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
    _build_rag_index()


def _split_sentences(text: str) -> List[str]:
    """将答案切分为适合检索展示的知识片段。"""
    text = (text or '').strip()
    if not text:
        return []
    parts = re.split(r'(?<=[。！？；;])\s*|\n+', text)
    sentences = [p.strip() for p in parts if p and p.strip()]
    if not sentences:
        return [text]

    chunks = []
    buf = ''
    for sent in sentences:
        if not buf:
            buf = sent
        elif len(buf) + len(sent) <= 180:
            buf += sent
        else:
            chunks.append(buf)
            buf = sent
    if buf:
        chunks.append(buf)
    return chunks


def _rag_tokens(text: str) -> List[str]:
    """轻量中文检索分词：关键词 + 中文 2/3-gram，完全离线无第三方依赖。"""
    norm = _normalize_text(text)
    if not norm:
        return []

    tokens = []
    for seg in re.split(r'[^\w\u4e00-\u9fff]+', text.lower()):
        seg = seg.strip()
        if len(seg) >= 2 and seg not in RAG_STOP_WORDS:
            tokens.append(seg)

    chinese = ''.join(re.findall(r'[\u4e00-\u9fff]', norm))
    for n in (2, 3):
        for i in range(max(0, len(chinese) - n + 1)):
            token = chinese[i:i+n]
            if token not in RAG_STOP_WORDS:
                tokens.append(token)

    # 保序去重，避免少量重复词过度放大
    seen = set()
    unique = []
    for token in tokens:
        if token and token not in seen:
            seen.add(token)
            unique.append(token)
    return unique


def _expand_query_text(query: str) -> str:
    """本地查询扩展，弥补中文短问句缺少显式知识库关键词的问题。"""
    norm = _normalize_text(query)
    expansions = []
    for triggers, expansion in RAG_QUERY_EXPANSIONS:
        for trigger in triggers:
            if _normalize_text(trigger) in norm:
                expansions.append(expansion)
                break
    if not expansions:
        return query
    return query + ' ' + ' '.join(expansions)


def _hash_embedding(text: str, dimension: int = 384) -> List[float]:
    """Deterministic offline fallback. It is not semantic and is never reported as model RAG."""
    vector = [0.0] * dimension
    for token in _rag_tokens(text):
        digest = hashlib.sha256(token.encode('utf-8')).digest()
        index = int.from_bytes(digest[:4], 'big') % dimension
        sign = 1.0 if digest[4] % 2 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _load_embedding_model() -> None:
    """Load an optional multilingual embedding model without making startup depend on it."""
    global RAG_EMBEDDING_MODEL, RAG_EMBEDDING_BACKEND, RAG_EMBEDDING_DIM
    if RAG_EMBEDDING_MODEL is not None or RAG_EMBEDDING_BACKEND != 'disabled':
        return
    if not RAG_ENABLE_EMBEDDING:
        RAG_EMBEDDING_BACKEND = 'disabled'
        return
    try:
        from sentence_transformers import SentenceTransformer

        model_path = os.environ.get('RAG_EMBEDDING_MODEL_PATH', '').strip()
        model_name = model_path or RAG_EMBEDDING_MODEL_NAME
        RAG_EMBEDDING_MODEL = SentenceTransformer(model_name)
        probe = RAG_EMBEDDING_MODEL.encode(['probe'], normalize_embeddings=True)
        RAG_EMBEDDING_DIM = len(probe[0])
        RAG_EMBEDDING_BACKEND = 'sentence-transformers'
        logger.info(f"Embedding模型已启用: {model_name}, dim={RAG_EMBEDDING_DIM}")
    except Exception as exc:
        # Do not download or fabricate a semantic model during an offline startup.
        RAG_EMBEDDING_MODEL = None
        RAG_EMBEDDING_BACKEND = 'unavailable'
        logger.warning(f"Embedding模型不可用，将仅使用词法召回: {exc}")


def _encode_texts(texts: List[str]) -> List[List[float]]:
    _load_embedding_model()
    if RAG_EMBEDDING_MODEL is None:
        return []
    try:
        vectors = RAG_EMBEDDING_MODEL.encode(texts, normalize_embeddings=True)
        return [list(map(float, vector)) for vector in vectors]
    except Exception as exc:
        logger.warning(f"Embedding编码失败: {exc}")
        return []


def _cosine_similarity(left: List[float], right: List[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def _rerank_candidates(query: str, candidates: List[Tuple[float, Dict]]) -> List[Tuple[float, Dict]]:
    """Second-stage reranking over hybrid-retrieval candidates."""
    query_norm = _normalize_text(query)
    query_tokens = set(_rag_tokens(query))
    reranked = []
    for retrieval_score, chunk in candidates:
        title = chunk.get('title', '')
        title_norm = _normalize_text(title)
        title_tokens = set(_rag_tokens(title))
        overlap = len(query_tokens & title_tokens) / max(len(query_tokens), 1)
        exact_bonus = 0.18 if query_norm == title_norm else 0.0
        title_bonus = 0.08 if query_norm and query_norm in title_norm else 0.0
        type_bonus = 0.04 if chunk.get('chunk_type') == 'qa_full' else 0.0
        rerank_score = retrieval_score * (1.0 + exact_bonus + title_bonus + type_bonus)
        rerank_score += 0.15 * overlap
        chunk['rerank_score'] = rerank_score
        reranked.append((rerank_score, chunk))
    reranked.sort(key=lambda item: item[0], reverse=True)
    return reranked


def _load_embedding_cache() -> Dict[str, List[float]]:
    try:
        with open(RAG_EMBEDDING_CACHE_FILE, 'r', encoding='utf-8') as handle:
            payload = json.load(handle)
        return payload.get('embeddings', {}) if isinstance(payload, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _save_embedding_cache(cache: Dict[str, List[float]]) -> None:
    try:
        os.makedirs(os.path.dirname(RAG_EMBEDDING_CACHE_FILE), exist_ok=True)
        with open(RAG_EMBEDDING_CACHE_FILE, 'w', encoding='utf-8') as handle:
            json.dump({
                'model': RAG_EMBEDDING_MODEL_NAME,
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'embeddings': cache,
            }, handle, ensure_ascii=False)
    except OSError as exc:
        logger.warning(f"保存Embedding缓存失败: {exc}")


def _build_rag_index():
    """从 Excel 问答对构建本地 RAG 知识库索引。"""
    global RAG_CHUNKS, RAG_DOC_FREQ, RAG_AVG_DOC_LEN

    chunks = []
    chunk_id = 1
    for idx, qa in enumerate(QA_DIRECT, start=1):
        question = qa.get('question', '').strip()
        answer = qa.get('answer', '').strip()
        if not question or not answer:
            continue

        base_meta = {
            'question': question,
            'answer': answer,
            'source': 'question.xlsx + answer.xlsx',
            'source_id': f'qa-{idx}',
        }
        full_text = f"问题：{question}\n答案：{answer}"
        chunks.append({
            **base_meta,
            'id': f'chunk-{chunk_id}',
            'title': question,
            'content': full_text,
            'chunk_type': 'qa_full',
        })
        chunk_id += 1

        for sentence in _split_sentences(answer):
            if sentence == answer and len(answer) < 220:
                continue
            chunks.append({
                **base_meta,
                'id': f'chunk-{chunk_id}',
                'title': question,
                'content': sentence,
                'chunk_type': 'answer_evidence',
            })
            chunk_id += 1

    doc_freq: Dict[str, int] = {}
    total_len = 0
    for chunk in chunks:
        weighted_text = f"{chunk['title']} {chunk['title']} {chunk['content']}"
        tokens = _rag_tokens(weighted_text)
        chunk['tokens'] = tokens
        chunk['token_counts'] = {t: tokens.count(t) for t in set(tokens)}
        total_len += len(tokens)
        for token in set(tokens):
            doc_freq[token] = doc_freq.get(token, 0) + 1

    # Build a persistent vector index when sentence-transformers is installed.
    _load_embedding_model()
    if RAG_EMBEDDING_MODEL is not None and chunks:
        cache = _load_embedding_cache()
        pending = []
        pending_keys = []
        for chunk in chunks:
            cache_key = hashlib.sha256(
                f"{RAG_EMBEDDING_MODEL_NAME}\n{chunk['content']}".encode('utf-8')
            ).hexdigest()
            chunk['embedding_key'] = cache_key
            if cache_key in cache:
                chunk['embedding'] = cache[cache_key]
            else:
                pending.append(chunk['content'])
                pending_keys.append(cache_key)
        vectors = _encode_texts(pending)
        for key, vector in zip(pending_keys, vectors):
            cache[key] = vector
        for chunk in chunks:
            if 'embedding' not in chunk and chunk.get('embedding_key') in cache:
                chunk['embedding'] = cache[chunk['embedding_key']]
        if vectors:
            _save_embedding_cache(cache)

    RAG_CHUNKS = chunks
    RAG_DOC_FREQ = doc_freq
    RAG_AVG_DOC_LEN = total_len / len(chunks) if chunks else 0.0
    logger.info(f"RAG索引构建完成: {len(RAG_CHUNKS)} 个知识块, {len(RAG_DOC_FREQ)} 个检索词")


def get_rag_stats() -> Dict:
    """返回 RAG 知识库状态。"""
    return {
        'questions_count': len(QUESTIONS),
        'qa_pairs_count': len(QA_PAIRS),
        'qa_direct_count': len(QA_DIRECT),
        'chunks_count': len(RAG_CHUNKS),
        'terms_count': len(RAG_DOC_FREQ),
        'avg_doc_len': round(RAG_AVG_DOC_LEN, 2),
        'embedding_backend': RAG_EMBEDDING_BACKEND,
        'embedding_dim': RAG_EMBEDDING_DIM,
        'vector_chunks_count': sum(1 for chunk in RAG_CHUNKS if chunk.get('embedding')),
        'llm_enabled': RAG_ENABLE_LLM,
        'data_dir': DATA_DIR,
    }


def retrieve_knowledge(query: str, top_k: int = 5) -> List[Dict]:
    """问题检索：返回最相关知识块及可解释评分。"""
    query = (query or '').strip()
    if not query or not RAG_CHUNKS:
        return []

    expanded_query = _expand_query_text(query)
    query_tokens = _rag_tokens(expanded_query)
    if not query_tokens:
        return []

    query_norm = _normalize_text(query)
    query_vector = _encode_texts([expanded_query])
    query_vector = query_vector[0] if query_vector else []
    total_docs = max(len(RAG_CHUNKS), 1)
    avg_len = RAG_AVG_DOC_LEN or 1.0
    scored = []

    for chunk in RAG_CHUNKS:
        score = 0.0
        doc_len = max(len(chunk.get('tokens', [])), 1)
        counts = chunk.get('token_counts', {})
        for token in query_tokens:
            tf = counts.get(token, 0)
            if not tf:
                continue
            df = RAG_DOC_FREQ.get(token, 0)
            idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
            denom = tf + 1.2 * (1 - 0.75 + 0.75 * doc_len / avg_len)
            score += idf * (tf * 2.2 / denom)

        title_norm = _normalize_text(chunk.get('title', ''))
        content_norm = _normalize_text(chunk.get('content', ''))
        expanded_norm = _normalize_text(expanded_query)
        if query_norm == title_norm:
            score += 10.0
        elif query_norm and (query_norm in title_norm or title_norm in query_norm):
            score += 5.0
        elif expanded_norm and title_norm and any(_normalize_text(term) in expanded_norm for term in chunk.get('title', '').split()):
            score += 1.0
        if query_norm and query_norm in content_norm:
            score += 2.5

        lexical_score = score
        vector_score = _cosine_similarity(query_vector, chunk.get('embedding', []))
        # Hybrid retrieval: semantic score improves paraphrase recall while lexical
        # matches remain dominant for dosage and contraindication wording.
        if query_vector and chunk.get('embedding'):
            score = 0.55 * min(lexical_score / 10.0, 1.0) + 0.45 * max(vector_score, 0.0)
            score *= 10.0

        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored:
        return []

    scored = _rerank_candidates(query, scored[:max(top_k * 4, 12)])
    best_score = scored[0][0]
    results = []
    seen_content = set()
    for score, chunk in scored[:max(top_k * 2, top_k)]:
        key = (chunk.get('source_id'), chunk.get('content'))
        if key in seen_content:
            continue
        seen_content.add(key)
        results.append({
            'id': chunk['id'],
            'title': chunk['title'],
            'content': chunk['content'],
            'question': chunk['question'],
            'source': chunk['source'],
            'source_id': chunk['source_id'],
            'chunk_type': chunk['chunk_type'],
            'score': round(score, 4),
            'lexical_score': round(lexical_score, 4),
            'vector_score': round(vector_score, 4),
            'rerank_score': round(chunk.get('rerank_score', score), 4),
            'confidence': round(min(score / max(best_score, 0.0001), 1.0), 4),
        })
        if len(results) >= top_k:
            break
    return results


def generate_grounded_answer(query: str, contexts: List[Dict]) -> Dict:
    """基于检索证据生成回答。离线版采用证据抽取式生成，避免无依据编造。"""
    if not contexts:
        return {
            'success': True,
            'answer': '抱歉，知识库中没有检索到足够相关的内容，建议换一种问法或咨询专业医师。',
            'source': 'none',
            'matched_question': None,
            'confidence': 0.0,
            'citations': [],
            'retrieval': [],
        }

    top = contexts[0]
    top_score = top.get('score', 0.0)
    if top_score < 1.2:
        return {
            'success': True,
            'answer': '抱歉，知识库中没有检索到足够相关的内容，建议从快捷问题中选择或咨询专业医师。',
            'source': 'rag_low_confidence',
            'matched_question': top.get('question'),
            'confidence': round(min(top_score / 4.0, 0.45), 4),
            'citations': contexts[:3],
            'retrieval': contexts,
        }

    matched_question = top.get('question')
    matched_answer = None
    for qa in QA_DIRECT:
        if qa.get('question') == matched_question:
            matched_answer = qa.get('answer')
            break

    if not matched_answer:
        matched_answer = top.get('content', '')

    confidence = min(0.98, max(0.55, top_score / 8.0))
    llm_answer = _generate_with_llm(query, contexts)
    if llm_answer:
        matched_answer = llm_answer
    return {
        'success': True,
        'answer': matched_answer,
        'source': 'rag_llm' if llm_answer else 'rag',
        'matched_question': matched_question,
        'confidence': round(confidence, 4),
        'citations': contexts[:3],
        'retrieval': contexts,
    }


def _generate_with_llm(query: str, contexts: List[Dict]) -> Optional[str]:
    """Call an optional OpenAI-compatible endpoint with strict evidence grounding."""
    if not RAG_ENABLE_LLM:
        return None
    endpoint = os.environ.get('RAG_LLM_ENDPOINT', '').strip()
    api_key = os.environ.get('RAG_LLM_API_KEY', '').strip()
    model = os.environ.get('RAG_LLM_MODEL', '').strip()
    if not endpoint or not model:
        logger.warning('RAG_ENABLE_LLM 已开启，但未配置 RAG_LLM_ENDPOINT 或 RAG_LLM_MODEL')
        return None
    evidence = '\n\n'.join(
        f"[{index}] {item.get('title', '')}\n{item.get('content', '')}"
        for index, item in enumerate(contexts[:5], start=1)
    )
    payload = json.dumps({
        'model': model,
        'temperature': 0.1,
        'messages': [
            {
                'role': 'system',
                'content': (
                    '你是香连止痢丸用药问答助手。只能依据给定证据回答，'
                    '不得补充证据之外的医学事实。证据不足时明确说无法确认。'
                    '回答简洁，并在相关句末使用[1]、[2]形式引用证据。'
                ),
            },
            {'role': 'user', 'content': f'用户问题：{query}\n\n证据：\n{evidence}'},
        ],
    }).encode('utf-8')
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            'Content-Type': 'application/json',
            **({'Authorization': f'Bearer {api_key}'} if api_key else {}),
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=float(os.environ.get('RAG_LLM_TIMEOUT', '12'))) as response:
            body = json.loads(response.read().decode('utf-8'))
        answer = body.get('choices', [{}])[0].get('message', {}).get('content', '')
        return answer.strip() or None
    except (OSError, ValueError, KeyError, IndexError, urllib.error.URLError) as exc:
        logger.warning(f'LLM生成失败，回退抽取式答案: {exc}')
        return None


def answer_with_rag(question: str, top_k: int = 5) -> Dict:
    """完整 RAG 流程：检索 → 证据排序 → 基于证据生成回答。"""
    contexts = retrieve_knowledge(question, top_k=top_k)
    return generate_grounded_answer(question, contexts)


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
    rag_result = answer_with_rag(question, top_k=3)
    if rag_result.get('source') == 'rag':
        return rag_result.get('answer'), rag_result.get('matched_question')
    return find_answer_by_question(question)


def get_recommended_questions(question: str, limit: int = 5) -> List[str]:
    """获取推荐问题"""
    retrieved = retrieve_knowledge(question, top_k=limit + 3)
    recommendations = []
    for item in retrieved:
        q = item.get('question')
        if q and q not in recommendations and _normalize_text(q) != _normalize_text(question):
            recommendations.append(q)
        if len(recommendations) >= limit:
            return recommendations
    for q in find_similar_questions(question, exclude=question, limit=limit):
        if q not in recommendations:
            recommendations.append(q)
        if len(recommendations) >= limit:
            break
    return recommendations


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
    result = answer_with_rag(question)
    result['question'] = result.get('matched_question') or question
    return result


def get_recommendations(question: str, limit: int = 5) -> List[str]:
    """获取推荐问题（别名）"""
    return get_recommended_questions(question, limit)
