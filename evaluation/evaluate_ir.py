from pathlib import Path
import csv
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.bm25 import BM25Search
from app.services.embeddings import semantic_scores

DATA_DIR = ROOT / "data"
GOLD_PATH = ROOT / "evaluation" / "gold_queries.csv"


def load_kb():
    records = []
    with (DATA_DIR / "knowledge_base.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["status"] == "approved":
                records.append({
                    "doc_id": row["doc_id"],
                    "text": f"{row['title']} {row['body']} {row['category']}",
                })
    return records


def load_gold():
    rows = []
    with GOLD_PATH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw = (row.get("relevant_doc_ids") or "").strip()
            relevant = {doc_id for doc_id in raw.split("|") if doc_id.strip()}
            rows.append((row["query"], relevant))
    return rows


def rank_indices(method, query, texts):
    bm25 = BM25Search(texts).scores(query)
    sem = semantic_scores(query, texts)
    if method == "BM25":
        score = bm25
    elif method == "Semantic":
        score = sem
    else:
        score = 0.45 * bm25 + 0.55 * sem
    return np.argsort(score)[::-1]


def metrics_for_query(ranked_ids, relevant, k=5):
    topk = ranked_ids[:k]
    hits = sum(1 for doc_id in topk if doc_id in relevant)
    precision = hits / k
    recall = hits / len(relevant) if relevant else 0.0
    rr = 0.0
    for rank, doc_id in enumerate(ranked_ids, start=1):
        if doc_id in relevant:
            rr = 1.0 / rank
            break
    precision_at_1 = 1.0 if ranked_ids[:1] and ranked_ids[0] in relevant else 0.0
    return precision_at_1, precision, recall, rr


def evaluate(method, records, gold):
    texts = [r["text"] for r in records]
    doc_ids = [r["doc_id"] for r in records]
    values = []
    for query, relevant in gold:
        order = rank_indices(method, query, texts)
        ranked_ids = [doc_ids[int(i)] for i in order]
        values.append(metrics_for_query(ranked_ids, relevant, k=5))
    arr = np.array(values)
    return arr.mean(axis=0)


def per_query_detail(records, gold, query_text=None, limit=5):
    texts = [r["text"] for r in records]
    doc_ids = [r["doc_id"] for r in records]
    target_queries = []
    if query_text:
        target_queries = [(query_text, next((relevant for q, relevant in gold if q.lower() == query_text.lower()), set()))]
    else:
        target_queries = gold[:3]

    for query, relevant in target_queries:
        print(f"\nQuery: {query}")
        print(f"Relevant: {', '.join(sorted(relevant)) if relevant else 'No relevant KB answer'}")
        for method in ["BM25", "Semantic", "Hybrid"]:
            order = rank_indices(method, query, texts)
            ranked_ids = [doc_ids[int(i)] for i in order[:limit]]
            print(f"{method} top result: {ranked_ids[0] if ranked_ids else 'None'}")
            print(f"{method} top {limit}: {', '.join(ranked_ids) if ranked_ids else 'None'}")


if __name__ == "__main__":
    records = load_kb()
    gold = load_gold()
    print(f"Evaluating {len(gold)} queries against {len(records)} KB articles\n")
    print(f"{'Method':<12} {'P@1':>8} {'P@5':>8} {'Recall@5':>10} {'MRR':>8}")
    print("-" * 58)
    for method in ["BM25", "Semantic", "Hybrid"]:
        p1, p5, r5, mrr = evaluate(method, records, gold)
        print(f"{method:<12} {p1:>8.3f} {p5:>8.3f} {r5:>10.3f} {mrr:>8.3f}")

    print("\nPer-query examples:\n")
    per_query_detail(records, gold, query_text="VPN disconnects every few minutes")
