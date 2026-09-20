from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.database import get_session
from app.schemas import AgentMessage
from app.agents.security_agent import check_input
from app.agents.ticket_agent import analyze_ticket
from app.agents.retrieval_agent import search_knowledge
from app.agents.solution_agent import recommend_solution
from app.agents.knowledge_intelligence_agent import analyze_knowledge_health

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/security/check")
def security_check(message: AgentMessage):
    return check_input(str(message.payload.get("text", "")))


@router.post("/ticket/analyze")
def ticket_analyze(message: AgentMessage):
    return analyze_ticket(str(message.payload.get("text", "")))


@router.post("/retrieval/search")
def retrieval_search(message: AgentMessage, session: Session = Depends(get_session)):
    return search_knowledge(session, str(message.payload.get("issue", "")))


@router.post("/solution/recommend")
def solution_recommend(message: AgentMessage):
    query = str(message.payload.get("query", ""))
    retrieval = message.payload.get("retrieval")
    if not isinstance(retrieval, dict):
        raise HTTPException(status_code=422, detail="payload.retrieval must be an object")
    return recommend_solution(query, retrieval)


@router.post("/knowledge/analyze")
def knowledge_analyze(session: Session = Depends(get_session)):
    return analyze_knowledge_health(session)
