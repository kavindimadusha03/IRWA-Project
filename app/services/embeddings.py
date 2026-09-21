from functools import lru_cache
from typing import Iterable, List, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer("all-MiniLM-L6-v2")


@lru_cache(maxsize=128)
def get_document_embeddings(documents_key: Tuple[str, ...]) -> np.ndarray:
    if not documents_key:
        return np.empty((0, 384), dtype=float)
    model = get_model()
    embeddings = model.encode(
        list(documents_key),
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(embeddings, dtype=float)


def clear_document_embedding_cache() -> None:
    get_document_embeddings.cache_clear()


def encode_texts(texts: List[str]) -> np.ndarray:
    if not texts:
        return np.empty((0, 384), dtype=float)
    return get_document_embeddings(tuple(texts))


def semantic_scores(query: str, documents: List[str]) -> np.ndarray:
    if not documents:
        return np.array([], dtype=float)
    model = get_model()
    query_vec = model.encode([query], normalize_embeddings=True, show_progress_bar=False)
    doc_vecs = get_document_embeddings(tuple(documents))
    scores = cosine_similarity(query_vec, doc_vecs)[0]
    return np.clip(scores, 0.0, 1.0)
