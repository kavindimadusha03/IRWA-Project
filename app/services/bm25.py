import re
from typing import List
import numpy as np
from rank_bm25 import BM25Okapi

TOKEN_RE = re.compile(r"[A-Za-z0-9_.:/\\-]+")


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


class BM25Search:
    def __init__(self, documents: List[str]):
        self.documents = documents
        self.tokenized = [tokenize(doc) for doc in documents]
        self.model = BM25Okapi(self.tokenized) if self.tokenized else None

    def scores(self, query: str) -> np.ndarray:
        if self.model is None:
            return np.array([], dtype=float)
        raw = np.array(self.model.get_scores(tokenize(query)), dtype=float)
        if len(raw) == 0:
            return raw
        min_v = float(raw.min())
        max_v = float(raw.max())
        if max_v - min_v < 1e-9:
            return np.zeros_like(raw)
        return (raw - min_v) / (max_v - min_v)
