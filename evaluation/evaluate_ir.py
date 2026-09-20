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
            rows.append((row["query"], set(row["relevant_doc_ids"].split("|"))))
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
    return precision, recall, rr


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


if __name__ == "__main__":
    records = load_kb()
    gold = load_gold()
    print(f"Evaluating {len(gold)} queries against {len(records)} KB articles\n")
    print(f"{'Method':<12} {'P@5':>8} {'Recall@5':>10} {'MRR':>8}")
    print("-" * 42)
    for method in ["BM25", "Semantic", "Hybrid"]:
        p5, r5, mrr = evaluate(method, records, gold)
        print(f"{method:<12} {p5:>8.3f} {r5:>10.3f} {mrr:>8.3f}")
