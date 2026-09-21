import re
from typing import List

import numpy as np
from rank_bm25 import BM25Okapi

TOKEN_RE = re.compile(
    r"0x[0-9A-Fa-f]+|[A-Za-z0-9]+(?:[._:/-][A-Za-z0-9]+)*|[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)+"
)
PRESERVED_COMMANDS = {
    "arp",
    "certutil",
    "chkdsk",
    "cmd",
    "diskpart",
    "driverquery",
    "getmac",
    "hostname",
    "ipconfig",
    "msinfo32",
    "netstat",
    "nslookup",
    "ping",
    "route",
    "sc",
    "sfc",
    "svc",
    "taskkill",
    "tasklist",
    "tracert",
    "whoami",
    "winver",
}


def tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    for match in TOKEN_RE.findall(text):
        value = match.lower()
        if "/" in value:
            tokens.extend(part.lower() for part in value.split("/") if part)
            continue
        if value in PRESERVED_COMMANDS or value.startswith("0x") or value.endswith(".exe"):
            tokens.append(value)
            continue
        tokens.append(value)
    return tokens


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
