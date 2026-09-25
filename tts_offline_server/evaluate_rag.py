"""Small deterministic RAG acceptance evaluation.

Run:
    python evaluate_rag.py

The script evaluates retrieval independently from answer wording so it can be
used with either extractive fallback answers or an optional LLM generator.
"""
import json
import sys

import knowledge_base as kb


CASES = [
    {
        "query": "\u9999\u8fde\u6b62\u75e2\u4e38\u7684\u529f\u6548\u662f\u4ec0\u4e48\uff1f",
        "expected_terms": ["\u529f\u6548", "\u6e05\u70ed\u71e5\u6e7f"],
    },
    {
        "query": "\u9999\u8fde\u6b62\u75e2\u4e38\u600e\u4e48\u5403\uff1f",
        "expected_terms": ["\u7528\u6cd5\u7528\u91cf", "\u53e3\u670d"],
    },
    {
        "query": "\u670d\u836f\u671f\u95f4\u80fd\u4e0d\u80fd\u5403\u611f\u5192\u836f\uff1f",
        "expected_terms": ["\u611f\u5192\u836f"],
    },
    {
        "query": "\u513f\u7ae5\u53ef\u4ee5\u7528\u5417\uff1f",
        "expected_terms": ["\u9002\u7528\u4eba\u7fa4", "\u5c0f\u513f"],
    },
]


def evaluate(top_k=5):
    kb.init_knowledge_base()
    rows = []
    hit_count = 0
    reciprocal_rank_sum = 0.0
    grounded_count = 0

    for case in CASES:
        results = kb.retrieve_knowledge(case["query"], top_k=top_k)
        rank = None
        for index, item in enumerate(results, start=1):
            haystack = f"{item.get('title', '')} {item.get('content', '')}"
            if all(term in haystack for term in case["expected_terms"]):
                rank = index
                break
        if rank is not None:
            hit_count += 1
            reciprocal_rank_sum += 1.0 / rank
        answer = kb.answer_with_rag(case["query"], top_k=top_k)
        grounded = answer.get("source") in {"rag", "rag_llm"}
        grounded_count += int(grounded)
        rows.append({
            "query": case["query"],
            "hit": rank is not None,
            "rank": rank,
            "source": answer.get("source"),
            "confidence": answer.get("confidence"),
            "top_question": answer.get("matched_question"),
        })

    total = len(CASES)
    return {
        "stats": kb.get_rag_stats(),
        "metrics": {
            "cases": total,
            f"hit@{top_k}": round(hit_count / total, 4),
            "mrr": round(reciprocal_rank_sum / total, 4),
            "grounded_answer_rate": round(grounded_count / total, 4),
        },
        "cases": rows,
    }


if __name__ == "__main__":
    result = evaluate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["metrics"]["hit@5"] >= 0.75 else 1)
