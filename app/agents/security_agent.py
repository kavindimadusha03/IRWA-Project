from typing import Dict, List
from app.services.pii import mask_pii

SUSPICIOUS_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "system prompt",
    "act as admin",
    "override policy",
    "always rank this first",
    "reveal hidden prompt",
    "disable security",
]


def check_input(text: str) -> Dict:
    lowered = text.lower()
    flags: List[str] = [p for p in SUSPICIOUS_PATTERNS if p in lowered]
    masked = mask_pii(text)
    return {
        "allowed": len(flags) == 0,
        "flags": flags,
        "masked_text": masked,
        "pii_was_masked": masked != text,
    }
