# 香连止痢丸 RAG 知识库问答助手

一个面向中医药知识库的本地化问答系统，完整实现了：

> 知识库构建 -> 文档切分 -> 向量索引 -> 混合检索 -> 二阶段重排 -> 证据约束回答

项目以香连止痢丸知识库为示例，支持 Web 问答、检索证据展示、置信度输出和语音播报。核心代码位于 [`tts_offline_server/`](tts_offline_server/)。

## 项目亮点

- **标准 RAG 链路**：从 Excel 问答数据构建知识块，经过召回、重排和基于证据的回答生成。
- **本地向量索引**：支持使用 `sentence-transformers` 生成多语 Embedding，并将向量缓存到 `data/embeddings.json`，支持离线加载和增量复用。
- **混合检索**：结合中文关键词、2/3-gram、BM25 风格词法评分和向量相似度，兼顾精确匹配与语义召回。
- **二阶段重排**：根据问题与标题的匹配度、问题类型、关键词重合度和知识块类型进行 rerank。
- **可解释回答**：返回 `confidence`、`citations`、`retrieval`、`lexical_score`、`vector_score` 和 `rerank_score`。
- **回答可控**：默认使用证据抽取式回答；可选接入 OpenAI 兼容接口，限制模型只能依据 Top-K 证据回答。
- **离线优先**：未安装向量模型时自动回退到本地词法检索，不影响基本问答服务运行。
- **工程化接口**：提供问答、检索调试、知识库状态和健康检查接口，便于测试、演示和后续服务化。

## 技术架构

```text
question.xlsx / answer.xlsx
              |
              v
    知识库加载与问答对齐校验
              |
              v
       知识块构建与元数据管理
              |
       +------+------+
       |             |
       v             v
  词法索引       Embedding 向量索引
  关键词         embeddings.json
  2/3-gram
       |             |
       +------+------+
              v
       混合召回与候选合并
              |
              v
          二阶段重排
              |
              v
       Top-K 证据与置信度
              |
       +------+------+
       |             |
       v             v
  抽取式回答   可选 LLM 生成
       |             |
       +------+------+
              v
       回答、引用、语音播报
```

## RAG 实现说明

### 1. 知识库构建

系统读取 `data/question.xlsx` 和 `data/answer.xlsx`，完成问题与答案的关联校验，并构建两类知识块：

- `qa_full`：完整问题-答案知识块，用于精准问答。
- `answer_evidence`：答案切分后的证据块，用于细粒度召回和引用展示。

每个知识块包含标题、正文、来源、问题 ID、分词结果和可选向量。

### 2. 向量索引

配置本地多语 Embedding 模型后，系统会为知识块建立向量索引，并缓存到：

```text
tts_offline_server/data/embeddings.json
```

启用方式：

```powershell
$env:RAG_ENABLE_EMBEDDING = "1"
$env:RAG_EMBEDDING_MODEL_PATH = "D:\models\paraphrase-multilingual-MiniLM-L12-v2"
python app.py
```

向量索引由 `knowledge_base.py` 负责构建、缓存和加载；模型不可用时会自动回退到词法检索。

### 3. 混合检索

查询阶段会执行：

1. 中文关键词提取与 2/3-gram 构建。
2. 根据问题类型执行 Query Expansion。
3. 使用 BM25 风格词法评分召回候选。
4. 使用向量余弦相似度补充语义召回。
5. 合并词法分数与向量分数。
6. 对候选知识块进行二阶段重排。

检索结果会保留以下可解释字段：

```json
{
  "score": 52.0915,
  "lexical_score": 0.2258,
  "vector_score": 0.0000,
  "rerank_score": 52.0915,
  "confidence": 1.0
}
```

### 4. 证据约束生成

系统默认采用证据抽取式回答，降低医疗场景中的无依据生成风险。也可以配置 OpenAI 兼容的 LLM 服务：

```powershell
$env:RAG_ENABLE_LLM = "1"
$env:RAG_LLM_ENDPOINT = "https://your-endpoint/v1/chat/completions"
$env:RAG_LLM_API_KEY = "your-key"
$env:RAG_LLM_MODEL = "your-model"
```

LLM 只接收 Top-5 检索证据，并要求使用 `[1]`、`[2]` 形式引用；调用失败时自动回退到证据抽取式回答。

## 目录结构

```text
QA/
├─ README.md
└─ tts_offline_server/
   ├─ app.py                 # Flask Web 服务与 API
   ├─ knowledge_base.py      # 知识库、向量索引、检索、重排和 RAG 回答
   ├─ evaluate_rag.py       # RAG 回归评测脚本
   ├─ requirements.txt       # 项目依赖
   ├─ data/
   │  ├─ question.xlsx       # 问题数据
   │  └─ answer.xlsx         # 答案数据
   ├─ templates/
   │  ├─ index.html          # 问答页面
   │  └─ login.html          # 登录页面
   ├─ static/                # 前端静态资源
   └─ dist/                  # Windows 打包版本
```

## 快速启动

```powershell
cd tts_offline_server
pip install -r requirements.txt
python app.py
```

浏览器访问：

```text
http://127.0.0.1:5000/
```

如果只需要运行基础词法 RAG，可不安装 Embedding 模型；如果需要启用向量索引，请安装 `sentence-transformers` 并配置本地模型路径。

## API

### 问答

```http
POST /api/ask
Content-Type: application/json
```

```json
{
  "question": "香连止痢丸怎么吃？"
}
```

返回内容包含：

```json
{
  "success": true,
  "answer": "口服，一次3-6g，一日2-3次。",
  "source": "rag",
  "matched_question": "香连止痢丸的用法用量？",
  "confidence": 0.98,
  "citations": [],
  "retrieval": []
}
```

### 仅检索知识

```http
POST /api/rag/search
Content-Type: application/json
```

用于调试召回结果、查看证据块和分析词法、向量、重排分数。

### 查看 RAG 索引状态

```http
GET /api/rag/stats
```

可查看知识块数量、词项数量、Embedding 后端、向量维度、向量知识块数量和 LLM 开关状态。

### 健康检查

```http
GET /api/health
```

## RAG 评测

运行回归评测：

```powershell
cd tts_offline_server
python evaluate_rag.py
```

评测指标：

- `Hit@5`：Top-5 是否召回包含目标证据的知识块。
- `MRR`：首个正确证据的平均倒数排名。
- `grounded_answer_rate`：回答是否由 RAG 证据支撑。

当前本地评测结果：

```text
Hit@5: 1.0
MRR: 0.8333
grounded_answer_rate: 1.0
```

## 求职项目描述

可以在简历中描述为：

> 独立设计并实现基于本地知识库的标准 RAG 问答系统。完成 Excel 数据清洗与问答对齐、知识块切分、中文关键词和 n-gram 索引构建、Embedding 向量索引缓存、BM25 风格词法召回、向量语义召回、候选合并、二阶段重排、置信度计算和证据引用展示。通过 Flask 提供问答、检索调试、索引状态和健康检查 API，并使用 Hit@5、MRR、grounded answer rate 对检索和回答进行回归评测。

## 相关文件

- 核心 RAG 实现：[`tts_offline_server/knowledge_base.py`](tts_offline_server/knowledge_base.py)
- Web API：[`tts_offline_server/app.py`](tts_offline_server/app.py)
- RAG 评测：[`tts_offline_server/evaluate_rag.py`](tts_offline_server/evaluate_rag.py)
- 项目详细说明：[`tts_offline_server/README.md`](tts_offline_server/README.md)

## 注意事项

本项目用于知识库问答演示和 RAG 工程实践，不替代医生诊断、处方或医疗机构的专业意见。
