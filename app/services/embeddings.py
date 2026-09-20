from functools import lru_cache
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer("all-MiniLM-L6-v2")


def encode_texts(texts: List[str]) -> np.ndarray:
    if not texts:
        return np.empty((0, 384), dtype=float)
    model = get_model()
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def semantic_scores(query: str, documents: List[str]) -> np.ndarray:
    if not documents:
        return np.array([], dtype=float)
    model = get_model()
    query_vec = model.encode([query], normalize_embeddings=True, show_progress_bar=False)
    doc_vecs = model.encode(documents, normalize_embeddings=True, show_progress_bar=False)
    scores = cosine_similarity(query_vec, doc_vecs)[0]
    return np.clip(scores, 0.0, 1.0)
