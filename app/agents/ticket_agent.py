import re
from typing import Dict
from app.services.llm import llm

ERROR_RE = re.compile(r"\b0x[0-9A-Fa-f]+\b")

CATEGORY_KEYWORDS = {
    "Wi-Fi / DNS": ["wifi", "wi-fi", "internet", "dns", "wireless", "network"],
    "VPN": ["vpn", "tunnel", "remote access"],
    "Outlook / MFA": ["outlook", "mfa", "email", "mail", "authenticator"],
    "Accounts / Passwords": ["password", "account", "login", "locked", "signin", "sign in"],
    "Printers": ["printer", "printing", "print queue", "toner"],
    "Windows / Updates": ["windows", "blue screen", "bsod", "update", "driver"],
    "Software Installation": ["install", "installation", "software", "application"],
    "Remote Desktop": ["rdp", "remote desktop", "remote session"],
}

PRIORITY_KEYWORDS = {
    "Critical": ["outage", "down", "unavailable", "cannot access", "locked out", "critical", "system is down", "no internet"],
    "High": ["vpn", "mfa", "login failed", "password reset", "remote desktop", "printer not working", "access denied"],
    "Medium": ["install", "update", "slow", "error", "cannot open", "network issue", "software"],
    "Low": ["question", "general", "minor", "simple", "how to"],
}

OS_NAMES = ["Windows 11", "Windows 10", "Ubuntu", "macOS", "Android", "iOS"]
APP_NAMES = ["Outlook", "Teams", "Chrome", "OneDrive", "VPN", "Office"]
DEVICE_NAMES = ["laptop", "desktop", "printer", "phone", "tablet"]


def _rule_category(text: str) -> str:
    lowered = text.lower()
    best = "Unknown"
    best_count = 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        count = sum(1 for k in keywords if k in lowered)
        if count > best_count:
            best = category
            best_count = count
    return best


def _entities(text: str) -> Dict:
    lowered = text.lower()
    error = ERROR_RE.search(text)
    os_name = next((x for x in OS_NAMES if x.lower() in lowered), None)
    app_name = next((x for x in APP_NAMES if x.lower() in lowered), None)
    device = next((x for x in DEVICE_NAMES if x in lowered), None)
    return {
        "error_code": error.group(0) if error else None,
        "os": os_name,
        "application": app_name,
        "device": device,
    }


def _rule_priority(text: str) -> str:
    lowered = text.lower()
    for priority, keywords in PRIORITY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return priority
    return "Medium"


def summarize_ticket_history(text: str, category: str, priority: str, canonical_issue: str) -> str:
    issue = (canonical_issue or text or "customer request").strip()
    issue = issue[:200]
    if not issue:
        return f"Issue classified as {category} with priority {priority}."
    return (
        f"Customer reported: {issue}. The case was classified as {category} with priority {priority}. "
        "The issue was reviewed against approved knowledge and a structured support recommendation was generated."
    )


def analyze_ticket(masked_text: str) -> Dict:
    category = _rule_category(masked_text)
    priority = _rule_priority(masked_text)
    entities = _entities(masked_text)
    canonical_issue = masked_text.strip()[:180]

    system = (
        "You are the Ticket Intelligence Agent for an IT support system. "
        "Return only valid JSON with keys category, canonical_issue, and priority. "
        "Use one category from: Wi-Fi / DNS, VPN, Outlook / MFA, Accounts / Passwords, "
        "Printers, Windows / Updates, Software Installation, Remote Desktop, Unknown. "
        "Use one priority from: Critical, High, Medium, Low. "
        "Do not invent facts. Keep canonical_issue under 25 words."
    )
    user = f"Ticket text:\n{masked_text}\nRule-based suggested category: {category}\nRule-based priority: {priority}"

    try:
        data = llm.chat_json(system, user)
        llm_category = str(data.get("category", category)).strip()
        llm_issue = str(data.get("canonical_issue", canonical_issue)).strip()
        llm_priority = str(data.get("priority", priority)).strip()
        allowed_categories = set(CATEGORY_KEYWORDS.keys()) | {"Unknown"}
        allowed_priorities = {"Critical", "High", "Medium", "Low"}
        if llm_category in allowed_categories:
            category = llm_category
        if llm_issue:
            canonical_issue = llm_issue[:180]
        if llm_priority in allowed_priorities:
            priority = llm_priority
    except Exception:
        pass

    return {
        "category": category,
        "canonical_issue": canonical_issue,
        "priority": priority,
        "entities": entities,
        "masked_text": masked_text,
        "history_summary": summarize_ticket_history(masked_text, category, priority, canonical_issue),
    }
