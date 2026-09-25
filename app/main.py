from datetime import date
from pathlib import Path
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.config import get_settings
from app.database import create_db_and_tables, get_session
from app.models import AgentLog, Category, KnowledgeArticle, Notification, SecurityEvent, SolutionFeedback, Ticket, TicketCitation, User
from app.notifications import get_user_notifications
from app.routes import admin, auth, tickets, support, knowledge, agents, chat
from app.routes.auth import current_user_from_request
from app.agents.ticket_agent import clarification_state_from_explanation
from app.agents.knowledge_intelligence_agent import (
    MAX_CLUSTER_TICKETS,
    MIN_CLUSTER_TICKETS,
    analyze_knowledge_health,
)
from evaluation.evaluate_ir import evaluate, load_gold, load_kb

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title=settings.app_name, version="1.0.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(support.router)
app.include_router(knowledge.router)
app.include_router(agents.router)
app.include_router(admin.router)
app.include_router(chat.router)


@app.on_event("startup")
def startup_event():
    create_db_and_tables()


@app.get("/", response_class=HTMLResponse)
def login_page(request: Request, session: Session = Depends(get_session)):
    user = current_user_from_request(request, session)
    if user:
        return RedirectResponse(url="/home", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/home", response_class=HTMLResponse)
def home(request: Request, session: Session = Depends(get_session)):
    user = current_user_from_request(request, session)
    if not user:
        return RedirectResponse(url="/", status_code=303)
    if user.role == "CUSTOMER":
        tickets_list = session.exec(select(Ticket).where(Ticket.user_id == user.id).order_by(Ticket.id.desc())).all()
        tickets_list = filter_tickets(tickets_list, request)
        notifications = get_user_notifications(session, user.id)
        return templates.TemplateResponse(
            "customer.html",
            {
                "request": request,
                "user": user,
                "tickets": tickets_list,
                "ticket_filters": ticket_filter_values(request),
                "notifications": notifications,
            },
        )
    if user.role in {"IT_SUPPORT", "ADMIN"}:
        return RedirectResponse(url="/support", status_code=303)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def ticket_result(ticket_id: int, request: Request, session: Session = Depends(get_session)):
    user = current_user_from_request(request, session)
    if not user:
        return RedirectResponse(url="/", status_code=303)
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if user.role == "CUSTOMER" and ticket.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    logs = session.exec(select(AgentLog).order_by(AgentLog.id.desc())).all()
    matching_logs = [log for log in logs if ticket.canonical_issue and ticket.canonical_issue[:40] in log.payload_summary]
    request_id = matching_logs[0].request_id if matching_logs else None
    if request_id:
        matching_logs = session.exec(
            select(AgentLog)
            .where(AgentLog.request_id == request_id)
            .order_by(AgentLog.id.asc())
        ).all()
    feedback = session.exec(
        select(SolutionFeedback).where(
            SolutionFeedback.ticket_id == ticket.id,
            SolutionFeedback.user_id == user.id,
        )
    ).first()
    citations = session.exec(
        select(TicketCitation)
        .where(TicketCitation.ticket_id == ticket.id)
        .order_by(TicketCitation.rank)
    ).all()
    citation_views = []
    for citation in citations:
        source_status = "resolved" if citation.source_type == "resolved_ticket" else "approved"
        supported_os = "Any"
        if citation.source_type == "internal_kb":
            article = session.exec(select(KnowledgeArticle).where(KnowledgeArticle.doc_id == citation.source_id)).first()
            if article:
                source_status = article.status
                supported_os = article.supported_os
        citation_views.append({
            "source_id": citation.source_id,
            "title": citation.title,
            "category": citation.category,
            "source_type": citation.source_type,
            "status": source_status,
            "supported_os": supported_os,
            "relevance_score": citation.relevance_score,
            "rank": citation.rank,
        })
    notifications = get_user_notifications(session, user.id)
    return templates.TemplateResponse(
        "ticket_result.html",
        {
            "request": request,
            "user": user,
            "ticket": ticket,
            "logs": matching_logs[:10],
            "trace_request_id": request_id,
            "feedback": feedback,
            "citations": citation_views,
            "clarification": clarification_state_from_explanation(ticket.decision_explanation),
            "notifications": notifications,
        },
    )


@app.get("/support", response_class=HTMLResponse)
def support_page(request: Request, session: Session = Depends(get_session)):
    user = current_user_from_request(request, session)
    if not user or user.role not in {"IT_SUPPORT", "ADMIN"}:
        raise HTTPException(status_code=403, detail="IT Support role required")
    queue = session.exec(select(Ticket).where(Ticket.status == "ESCALATED").order_by(Ticket.id.desc())).all()
    resolved = session.exec(select(Ticket).where(Ticket.status == "RESOLVED").order_by(Ticket.id.desc())).all()
    if user.role == "ADMIN":
        queue = []
    queue = filter_tickets(queue, request)
    resolved = filter_tickets(resolved, request)
    notifications = get_user_notifications(session, user.id)
    return templates.TemplateResponse(
        "support.html",
        {
            "request": request,
            "user": user,
            "queue": queue,
            "resolved": resolved[:20],
            "ticket_filters": ticket_filter_values(request),
            "notifications": notifications,
        },
    )


@app.get("/knowledge", response_class=HTMLResponse)
def knowledge_page(request: Request, session: Session = Depends(get_session)):
    user = current_user_from_request(request, session)
    if not user:
        return RedirectResponse(url="/", status_code=303)
    articles = session.exec(select(KnowledgeArticle).order_by(KnowledgeArticle.id.desc())).all()
    filters = knowledge_filter_values(request)
    articles = [
        article for article in articles
        if (not filters["category"] or article.category == filters["category"])
        and (not filters["os"] or filters["os"].lower() in article.supported_os.lower() or article.supported_os.lower() == "any")
        and (not filters["status"] or article.status == filters["status"])
        and (not filters["from_date"] or article.created_at.date() >= filters["from_date"])
        and (not filters["to_date"] or article.created_at.date() <= filters["to_date"])
    ]
    all_articles = session.exec(select(KnowledgeArticle).order_by(KnowledgeArticle.id.desc())).all()
    categories = session.exec(select(Category).where(Category.is_active == True).order_by(Category.name)).all()
    return templates.TemplateResponse(
        "knowledge.html",
        {"request": request, "user": user, "articles": articles, "all_articles": all_articles, "categories": categories, "knowledge_filters": filters},
    )


def parse_date(value: str | None):
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def ticket_filter_values(request: Request):
    return {
        "category": request.query_params.get("category", "").strip(),
        "status": request.query_params.get("status", "").strip(),
        "min_confidence": request.query_params.get("min_confidence", "").strip(),
        "from_date": parse_date(request.query_params.get("from_date")),
        "to_date": parse_date(request.query_params.get("to_date")),
    }


def filter_tickets(tickets, request: Request):
    filters = ticket_filter_values(request)
    try:
        minimum_confidence = float(filters["min_confidence"]) if filters["min_confidence"] else None
    except ValueError:
        minimum_confidence = None
    return [
        ticket for ticket in tickets
        if (not filters["category"] or ticket.category == filters["category"])
        and (not filters["status"] or ticket.status == filters["status"])
        and (minimum_confidence is None or ticket.retrieval_confidence >= minimum_confidence)
        and (not filters["from_date"] or ticket.created_at.date() >= filters["from_date"])
        and (not filters["to_date"] or ticket.created_at.date() <= filters["to_date"])
    ]


def knowledge_filter_values(request: Request):
    return {
        "category": request.query_params.get("category", "").strip(),
        "os": request.query_params.get("os", "").strip(),
        "status": request.query_params.get("status", "").strip(),
        "from_date": parse_date(request.query_params.get("from_date")),
        "to_date": parse_date(request.query_params.get("to_date")),
    }


def build_evaluation_metrics():
    try:
        records = load_kb()
        gold = load_gold()
    except Exception:
        return {}
    metrics = {}
    for method in ["BM25", "Semantic", "Hybrid"]:
        p1, p5, r5, mrr = evaluate(method, records, gold)
        metrics[method] = {
            "precision_at_5": round(float(p5), 3),
            "recall_at_5": round(float(r5), 3),
        }
    return metrics


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request, session: Session = Depends(get_session)):
    user = current_user_from_request(request, session)
    if not user or user.role != "KNOWLEDGE_ANALYST":
        raise HTTPException(status_code=403, detail="Knowledge Analyst role required")
    intelligence = analyze_knowledge_health(session)
    latest_log = session.exec(select(AgentLog).order_by(AgentLog.id.desc())).first()
    logs = []
    trace_request_id = latest_log.request_id if latest_log else None
    if trace_request_id:
        logs = session.exec(
            select(AgentLog)
            .where(AgentLog.request_id == trace_request_id)
            .order_by(AgentLog.id.asc())
        ).all()
    security_events = session.exec(select(SecurityEvent).order_by(SecurityEvent.id.desc())).all()[:50]
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "health": intelligence["health"],
            "clusters": intelligence["clusters"],
            "min_cluster_tickets": MIN_CLUSTER_TICKETS,
            "max_cluster_sample": MAX_CLUSTER_TICKETS,
            "logs": logs,
            "trace_request_id": trace_request_id,
            "security_events": security_events,
            "evaluation_metrics": build_evaluation_metrics(),
        },
    )


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
