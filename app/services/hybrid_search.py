import re
from difflib import get_close_matches
from typing import Dict, List

import numpy as np

from app.config import get_settings
from app.services.bm25 import BM25Search
from app.services.embeddings import semantic_scores

settings = get_settings()

COMMON_QUERY_REPLACEMENTS = {
    "connectef": "connected",
    "conected": "connected",
    "conneced": "connected",
    "connected": "connected",
    "connection": "connection",
    "interner": "internet",
    "internte": "internet",
    "intenet": "internet",
    "intenret": "internet",
    "internt": "internet",
    "wireless": "wifi",
    "wfi": "wifi",
    "wlan": "wifi",
    "wi-fi": "wifi",
    "wifi": "wifi",
    "bur": "but",
    "burt": "but",
    "cant": "cannot",
    "can't": "cannot",
    "cannot": "cannot",
    "doesnt": "does not",
    "doesn't": "does not",
    "dont": "do not",
    "don't": "do not",
    "failin": "failed",
    "failng": "failed",
    "failing": "failed",
    "fialed": "failed",
    "conn": "connect",
    "connt": "connect",
    "conx": "connect",
    "conection": "connection",
    "auth": "authentication",
    "authn": "authentication",
    "net": "internet",
    "nw": "network",
    "ntwk": "network",
    "pc": "computer",
    "comp": "computer",
    "laptop": "laptop",
    "lappy": "laptop",
    "err": "error",
    "errorr": "error",
    "unavail": "unavailable",
    "unavailable": "unavailable",
    "login": "login",
}

LOW_VALUE_QUERY_WORDS = {
    "a", "an", "and", "at", "for", "from", "in", "into", "is", "it",
    "my", "of", "on", "or", "really", "suddenly", "the", "there", "this", "to",
    "very", "when", "with", "just", "again", "still", "then", "so", "up", "out",
    "off", "keep", "keeps", "as", "be", "been", "have", "has", "had", "about"
}

PRESERVE_QUERY_TOKENS = {
    "wifi", "internet", "dns", "vpn", "rdp", "mfa", "laptop", "router", "network",
    "windows", "windows-11", "macbook", "surface", "printer", "phone", "pc", "computer",
    "connect", "connected", "connection", "cannot", "no", "not", "error", "failed",
    "timeout", "issue", "issues", "problem", "access", "authentication", "login", "logout",
    "router", "switch", "password", "configuration", "driver", "bluetooth", "credential",
    "proxy", "firewall", "permission", "permissions", "blue", "screen", "startup"
}

PHRASE_REPLACEMENTS = {
    "unable to": "cannot",
    "unable": "cannot",
    "not working": "issue",
    "no internet": "internet",
    "no wifi": "wifi",
    "no access": "access issue",
    "internet access": "internet",
    "wifi access": "wifi",
    "internet connectivity": "internet",
    "connection issue": "connectivity issue",
    "keeps failing": "failed",
    "kept failing": "failed",
    "keep failing": "failed",
    "can't connect": "cannot connect",
    "cant connect": "cannot connect",
}


def normalize_query_for_search(query: str, corpus_texts: List[str] | None = None) -> str:
    if not query:
        return ""

    text = query.lower().replace("&", " and ")
    for phrase, replacement in sorted(PHRASE_REPLACEMENTS.items(), key=lambda item: len(item[0]), reverse=True):
        text = re.sub(rf"\b{re.escape(phrase)}\b", replacement, text)

    text = re.sub(r"[^a-z0-9\s.-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    tokens = text.split()

    vocab = set()
    if corpus_texts:
        for doc in corpus_texts:
            vocab.update(re.findall(r"[a-z0-9-]+", doc.lower()))

    vocab |= set(COMMON_QUERY_REPLACEMENTS.values())
    vocab |= PRESERVE_QUERY_TOKENS
    vocab |= {"wifi", "internet", "connection", "authentication", "failed", "cannot", "connect"}

    normalized_tokens: List[str] = []
    for token in tokens:
        cleaned = token.strip()
        if not cleaned:
            continue

        if re.fullmatch(r"0x[a-f0-9]+", cleaned):
            normalized_tokens.append(cleaned)
            continue

        canonical = COMMON_QUERY_REPLACEMENTS.get(cleaned, cleaned)
        canonical = canonical.strip()

        if canonical in LOW_VALUE_QUERY_WORDS:
            continue

        if canonical in PRESERVE_QUERY_TOKENS:
            normalized_tokens.append(canonical)
            continue

        if canonical not in vocab and len(canonical) > 2:
            matches = get_close_matches(canonical, sorted(vocab), n=1, cutoff=0.72)
            if matches:
                canonical = matches[0]

        if canonical and canonical not in LOW_VALUE_QUERY_WORDS:
            normalized_tokens.append(canonical)

    # Ensure common technical tokens remain in the final query even when the original phrase is slightly malformed.
    final_tokens = []
    seen = set()
    for token in normalized_tokens:
        if token not in seen:
            final_tokens.append(token)
            seen.add(token)
    return " ".join(final_tokens)


def _extract_error_codes(text: str) -> set[str]:
    if not text:
        return set()
    return {match.lower() for match in re.findall(r"0x[a-f0-9]+", text.lower())}


def _deduplicate_records(records: List[Dict], similarity_threshold: float = 0.9) -> List[Dict]:
    if len(records) < 2:
        return records

    kept: List[Dict] = []
    for record in records:
        title = re.sub(r"\bguide\s*\d+\b", "", str(record.get("title", "")), flags=re.IGNORECASE)
        title_norm = re.sub(r"[^a-z0-9\s]", " ", title.lower())
        title_norm = re.sub(r"\s+", " ", title_norm).strip()
        content_norm = re.sub(r"[^a-z0-9\s]", " ", str(record.get("content", "")).lower())
        content_norm = re.sub(r"\s+", " ", content_norm).strip()
        category_norm = re.sub(r"[^a-z0-9\s]", " ", str(record.get("category", "")).lower())
        category_norm = re.sub(r"\s+", " ", category_norm).strip()

        is_duplicate = False
        for kept_record in kept:
            kept_title = re.sub(r"\bguide\s*\d+\b", "", str(kept_record.get("title", "")), flags=re.IGNORECASE)
            kept_title_norm = re.sub(r"[^a-z0-9\s]", " ", kept_title.lower())
            kept_title_norm = re.sub(r"\s+", " ", kept_title_norm).strip()
            kept_content_norm = re.sub(r"[^a-z0-9\s]", " ", str(kept_record.get("content", "")).lower())
            kept_content_norm = re.sub(r"\s+", " ", kept_content_norm).strip()
            kept_category_norm = re.sub(r"[^a-z0-9\s]", " ", str(kept_record.get("category", "")).lower())
            kept_category_norm = re.sub(r"\s+", " ", kept_category_norm).strip()

            title_match = title_norm and kept_title_norm and title_norm == kept_title_norm
            content_match = content_norm and kept_content_norm and content_norm == kept_content_norm
            if title_match or content_match:
                is_duplicate = True
                break

            if category_norm and category_norm == kept_category_norm:
                shared = len(set(content_norm.split()) & set(kept_content_norm.split()))
                total = len(set(content_norm.split()) | set(kept_content_norm.split()))
                if total and shared / total >= similarity_threshold:
                    is_duplicate = True
                    break

        if not is_duplicate:
            kept.append(record)
    return kept


def hybrid_rank(query: str, records: List[Dict], top_k: int = 5) -> List[Dict]:
    if not records:
        return []

    deduped_records = _deduplicate_records(records)
    texts = [f"{r['title']} {r['content']} {r.get('category', '')}" for r in deduped_records]
    normalized_query = normalize_query_for_search(query, texts)
    search_query = normalized_query if normalized_query else query

    query_error_codes = _extract_error_codes(query)
    bm25 = BM25Search(texts).scores(search_query)
    semantic = semantic_scores(search_query, texts)

    hybrid = (
        settings.hybrid_bm25_weight * bm25
        + settings.hybrid_semantic_weight * semantic
    )

    if query_error_codes:
        exact_match_bonus = 0.35
        for idx, record in enumerate(deduped_records):
            record_text = " ".join(
                str(record.get(field, ""))
                for field in ("title", "content", "category", "supported_os")
            )
            if query_error_codes & _extract_error_codes(record_text):
                hybrid[idx] += exact_match_bonus

    order = np.argsort(hybrid)[::-1][:top_k]
    results = []
    for idx in order:
        record = dict(deduped_records[int(idx)])
        exact_error_match = bool(query_error_codes and query_error_codes & _extract_error_codes(
            " ".join(str(record.get(field, "")) for field in ("title", "content", "category", "supported_os"))
        ))
        record["bm25_score"] = float(bm25[int(idx)])
        record["semantic_score"] = float(semantic[int(idx)])
        record["hybrid_score"] = float(hybrid[int(idx)])
        record["exact_error_match"] = exact_error_match
        results.append(record)
    return results
