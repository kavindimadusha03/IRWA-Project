from typing import Dict, List
import numpy as np
from app.config import get_settings
from app.services.bm25 import BM25Search
from app.services.embeddings import semantic_scores

settings = get_settings()


def hybrid_rank(query: str, records: List[Dict], top_k: int = 5) -> List[Dict]:
    if not records:
        return []

    texts = [f"{r['title']} {r['content']} {r.get('category', '')}" for r in records]
    bm25 = BM25Search(texts).scores(query)
    semantic = semantic_scores(query, texts)

    hybrid = (
        settings.hybrid_bm25_weight * bm25
        + settings.hybrid_semantic_weight * semantic
    )

    order = np.argsort(hybrid)[::-1][:top_k]
    results = []
    for idx in order:
        record = dict(records[int(idx)])
        record["bm25_score"] = float(bm25[int(idx)])
        record["semantic_score"] = float(semantic[int(idx)])
        record["hybrid_score"] = float(hybrid[int(idx)])
        results.append(record)
    return results
