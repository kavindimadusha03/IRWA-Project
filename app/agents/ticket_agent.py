import re
import json
from typing import Dict, List
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

_CONCRETE_DETAIL_PATTERNS = (
    r"\b0x[0-9a-f]+\b",
    r"\b(?:windows|ubuntu|macos|android|ios)\s*\d*\b",
    r"\b(?:since|after|before|when|only|just)\b",
    r"\b(?:error|fails?|failed|disconnect(?:s|ed|ing)?|timeout|slow|crash(?:es|ed)?)\b",
)

CLARIFICATION_STATE_PREFIX = "CLARIFICATION_STATE:"


def _sentences(text: str) -> List[str]:
    return [part.strip(" .") for part in re.split(r"[.!?\n]+", text or "") if part.strip()]


def _category_terms(category: str) -> List[str]:
    return [term for term in CATEGORY_KEYWORDS.get(category, []) if len(term) > 2]


def _sentence_mentions_category(sentence: str, category: str) -> bool:
    lowered = sentence.lower()
    if category == "Windows / Updates" and not any(term in lowered for term in ("update", "driver", "blue screen", "bsod")):
        return False
    return any(term in lowered for term in _category_terms(category))


def _is_confirmed_working(sentence: str, category: str) -> bool:
    if not _sentence_mentions_category(sentence, category):
        return False
    lowered = sentence.lower()
    if re.search(r"\bonly\b.*\b(?:affected|problem|issue|failing|disconnect)", lowered):
        return False
    return bool(re.search(
        r"\b(?:working|works|fine|okay|ok|normal|fixed|resolved|available)\b|\bno\s+(?:issues?|problems?)\b",
        lowered,
    )) and not bool(re.search(r"\b(?:not|isn't|isnt|aren't|arent|cannot|can't|cant|won't|wont)\s+(?:working|work|connect|access|open)\b", lowered))


def build_clarified_issue(original_text: str, clarification_text: str) -> Dict:
    """Extract a conservative, persisted issue representation from clarification text."""
    answers = clarification_text.strip()
    all_text = f"{original_text}\n{answers}".strip()
    sentences = _sentences(answers)
    categories = list(CATEGORY_KEYWORDS)
    negated: List[str] = []
    active_sentences: List[str] = []
    active_categories: List[str] = []

    for sentence in sentences:
        sentence_categories = [category for category in categories if _sentence_mentions_category(sentence, category)]
        if "VPN" in sentence_categories and "Accounts / Passwords" in sentence_categories:
            if not re.search(r"\b(?:password|account|locked|signin|sign in)\b", sentence.lower()):
                sentence_categories.remove("Accounts / Passwords")
        active_in_sentence = False
        for category in sentence_categories:
            if _is_confirmed_working(sentence, category):
                if category not in negated:
                    negated.append(category)
            else:
                active_in_sentence = True
                if category not in active_categories:
                    active_categories.append(category)
        if active_in_sentence:
            active_sentences.append(sentence)

    # A positive failure statement overrides an earlier broad description, while
    # explicit working statements remove those services from the effective query.
    for sentence in sentences:
        for category in categories:
            if _sentence_mentions_category(sentence, category) and category not in negated:
                if sentence not in active_sentences:
                    active_sentences.append(sentence)
                if category not in active_categories:
                    active_categories.append(category)

    if "VPN" in active_categories and "Accounts / Passwords" in active_categories:
        if not re.search(r"\b(?:password|account|locked|signin|sign in)\b", answers.lower()):
            active_categories.remove("Accounts / Passwords")

    os_name = next((name for name in OS_NAMES if name.lower() in answers.lower()), None)
    if len(active_categories) == 1:
        affected_service = active_categories[0]
    elif active_categories:
        affected_service = "Multiple services"
    else:
        affected_service = ""

    uncertainties: List[str] = []
    if not active_categories:
        uncertainties.append("The clarification does not identify an active affected service.")
    if not any(re.search(r"\b(?:fail|failed|disconnect|error|cannot|issue|problem|slow|crash|timeout|affected|not working)\w*\b", sentence.lower()) for sentence in active_sentences):
        uncertainties.append("The active symptom or failure behavior is not specific enough.")
    if not os_name:
        uncertainties.append("The affected operating system is not known.")

    effective_query = " ".join(active_sentences)
    if os_name and os_name.lower() not in effective_query.lower():
        effective_query = f"{effective_query} {os_name}".strip()

    return {
        "confirmed_active_symptoms": active_sentences,
        "resolved_or_negated_symptoms": sorted(set(negated)),
        "operating_system": os_name,
        "affected_service": affected_service,
        "original_context": original_text.strip()[:500],
        "remaining_uncertainties": uncertainties,
        "effective_query": effective_query[:500],
    }


def serialize_clarification_state(state: Dict) -> str:
    return CLARIFICATION_STATE_PREFIX + json.dumps(state, separators=(",", ":"), sort_keys=True)


def clarification_state_from_explanation(explanation: str) -> Dict:
    if not explanation or CLARIFICATION_STATE_PREFIX not in explanation:
        return {}
    encoded = explanation.split(CLARIFICATION_STATE_PREFIX, 1)[1].split("\n", 1)[0].strip()
    try:
        value = json.loads(encoded)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _category_hits(text: str) -> List[str]:
    lowered = text.lower()
    return [
        category
        for category, keywords in CATEGORY_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    ]


def _ambiguity_assessment(text: str, category: str) -> Dict:
    lowered = text.lower()
    hits = _category_hits(text)
    access_cluster = {"VPN", "Outlook / MFA", "Accounts / Passwords"}
    unrelated_hit_count = len(set(hits) - access_cluster) + (1 if set(hits) & access_cluster else 0)
    concrete_details = sum(bool(re.search(pattern, lowered)) for pattern in _CONCRETE_DETAIL_PATTERNS)
    broad_symptom = any(
        phrase in lowered
        for phrase in ("cannot connect to anything", "everything is not working", "nothing works", "all not working")
    )
    explicit_scope = any(
        phrase in lowered
        for phrase in ("only ", "but .* works", "while .* works", "other services work")
    )

    reasons: List[str] = []
    if unrelated_hit_count >= 3 and concrete_details <= 1 and (broad_symptom or not explicit_scope):
        reasons.append("The description names several services but does not identify one primary failing service.")
    if not text.strip() or len(text.split()) < 6:
        reasons.append("The description does not contain enough technical detail to select a safe procedure.")
    if category == "Unknown":
        reasons.append("The affected system or service is not clear from the description.")

    ambiguous = bool(reasons)
    questions = [
        "Which single service or device is the main problem right now?",
        "What exactly happens when you try it, and when did the problem start?",
        "Which operating system and device are affected, and do you see an error message or code?",
    ]
    if len(hits) == 1:
        questions[0] = f"Is {hits[0]} the only service or device affected, or are other services also failing?"

    return {
        "required": ambiguous,
        "reasons": reasons,
        "questions": questions,
        "category_hits": hits,
    }


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
        "The issue was reviewed against eligible knowledge sources and a structured support decision was generated."
    )


def analyze_ticket(masked_text: str, structured_issue: Dict | None = None) -> Dict:
    category = _rule_category(masked_text)
    priority = _rule_priority(masked_text)
    entities = _entities(masked_text)
    canonical_issue = masked_text.strip()[:180]
    ambiguity = _ambiguity_assessment(masked_text, category)
    if structured_issue:
        category = structured_issue.get("affected_service") or category
        if category == "Multiple services":
            category = "Unknown"
        ambiguity["required"] = bool(structured_issue.get("remaining_uncertainties")) or len(structured_issue.get("confirmed_active_symptoms", [])) > 1
        ambiguity["reasons"] = list(structured_issue.get("remaining_uncertainties", []))
        ambiguity["questions"] = [
            "Which one of the remaining affected services should IT Support investigate first?",
            "What exact failure do you see and when does it occur?",
            "What device and operating system are affected?",
        ] if ambiguity["required"] else []
        canonical_issue = structured_issue.get("effective_query") or canonical_issue

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
        if llm_category in allowed_categories and not ambiguity["required"] and category == "Unknown":
            category = llm_category
        if llm_issue and not structured_issue:
            canonical_issue = llm_issue[:180]
        if llm_priority in allowed_priorities:
            priority = llm_priority
    except Exception:
        pass

    if ambiguity["required"]:
        category = "Unknown"

    return {
        "category": category,
        "canonical_issue": canonical_issue,
        "priority": priority,
        "entities": entities,
        "masked_text": masked_text,
        "ambiguity_required": ambiguity["required"],
        "ambiguity_reasons": ambiguity["reasons"],
        "clarification_questions": ambiguity["questions"] if ambiguity["required"] else [],
        "category_hits": ambiguity["category_hits"],
        "history_summary": summarize_ticket_history(masked_text, category, priority, canonical_issue),
    }
