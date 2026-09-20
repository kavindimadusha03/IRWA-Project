import re

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?94|0)?7\d{8}(?!\d)")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
SECRET_RE = re.compile(r"(?i)\b(api[_ -]?key|password|token|secret)\s*[:=]\s*[^\s,;]+")


def mask_pii(text: str) -> str:
    text = EMAIL_RE.sub("[EMAIL]", text)
    text = PHONE_RE.sub("[PHONE]", text)
    text = IP_RE.sub("[IP]", text)
    text = SECRET_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    return text
