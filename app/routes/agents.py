from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session
from app.database import get_session
from app.schemas import AgentMessage
from app.agents.security_agent import check_input
from app.agents.ticket_agent import analyze_ticket
from app.agents.retrieval_agent import search_knowledge
from app.agents.solution_agent import recommend_solution
from app.agents.knowledge_intelligence_agent import analyze_knowledge_health
from app.routes.auth import current_user_from_request

router = APIRouter(prefix="/agents", tags=["agents"])


def _require_agent_user(request: Request, session: Session, roles=None):
    user = current_user_from_request(request, session)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Verified login required")
    if roles and user.role not in roles:
        raise HTTPException(status_code=403, detail="Insufficient role permissions")
    return user


def _payload_text(message: AgentMessage, key: str) -> str:
    value = message.payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(status_code=422, detail=f"payload.{key} must be a non-empty string")
    return value.strip()


@router.post("/security/check")
def security_check(message: AgentMessage, request: Request, session: Session = Depends(get_session)):
    _require_agent_user(request, session)
    return check_input(_payload_text(message, "text"))


@router.post("/ticket/analyze")
def ticket_analyze(message: AgentMessage, request: Request, session: Session = Depends(get_session)):
    _require_agent_user(request, session)
    return analyze_ticket(_payload_text(message, "text"))


@router.post("/retrieval/search")
def retrieval_search(message: AgentMessage, request: Request, session: Session = Depends(get_session)):
    _require_agent_user(request, session)
    return search_knowledge(session, _payload_text(message, "issue"))


@router.post("/solution/recommend")
def solution_recommend(message: AgentMessage, request: Request, session: Session = Depends(get_session)):
    _require_agent_user(request, session)
    query = _payload_text(message, "query")
    retrieval = search_knowledge(session, query)
    return recommend_solution(query, retrieval)


@router.post("/knowledge/analyze")
def knowledge_analyze(request: Request, session: Session = Depends(get_session)):
    _require_agent_user(request, session, {"KNOWLEDGE_ANALYST", "IT_SUPPORT", "ADMIN"})
    return analyze_knowledge_health(session)
