from datetime import datetime
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
from app.database import get_session
from app.models import KnowledgeArticle
from app.routes.auth import current_user_from_request

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _analyst_user(request: Request, session: Session):
    user = current_user_from_request(request, session)
    return user if user and user.role == "KNOWLEDGE_ANALYST" else None


def _redirect(message: str = "", error: str = ""):
    params = []
    if message:
        params.append(f"message={quote_plus(message)}")
    if error:
        params.append(f"error={quote_plus(error)}")
    suffix = f"?{'&'.join(params)}" if params else ""
    return RedirectResponse(url=f"/knowledge{suffix}", status_code=303)


def _article_by_doc_id(session: Session, doc_id: str, exclude_id: int | None = None):
    article = session.exec(select(KnowledgeArticle).where(KnowledgeArticle.doc_id == doc_id)).first()
    if article and article.id != exclude_id:
        return article
    return None


@router.post("/articles/{article_id}")
def update_article(
    article_id: int,
    request: Request,
    doc_id: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    category: str = Form(...),
    status: str = Form(...),
    supported_os: str = Form("Any"),
    session: Session = Depends(get_session),
):
    analyst = _analyst_user(request, session)
    if not analyst:
        raise HTTPException(status_code=403, detail="Knowledge Analyst role required")
    article = session.get(KnowledgeArticle, article_id)
    if not article:
        return _redirect(error="Article not found.")
    if status not in {"draft", "approved"} or not all(value.strip() for value in (doc_id, title, content, category)):
        return _redirect(error="Article fields are incomplete or invalid.")
    if _article_by_doc_id(session, doc_id.strip(), exclude_id=article.id):
        return _redirect(error="That document ID already exists.")
    article.doc_id = doc_id.strip()
    article.title = title.strip()
    article.content = content.strip()
    article.category = category.strip()
    article.status = status
    article.authoritative = status == "approved"
    article.supported_os = supported_os.strip() or "Any"
    article.updated_at = datetime.utcnow()
    session.add(article)
    session.commit()
    return _redirect(message="Knowledge article updated.")


@router.post("/{article_id}/approve")
def approve_article(article_id: int, request: Request, session: Session = Depends(get_session)):
    user = current_user_from_request(request, session)
    if not user or user.role != "KNOWLEDGE_ANALYST":
        raise HTTPException(status_code=403, detail="Knowledge Analyst role required")
    article = session.get(KnowledgeArticle, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article.status = "approved"
    article.authoritative = True
    article.updated_at = datetime.utcnow()
    session.add(article)
    session.commit()
    return RedirectResponse(url="/knowledge", status_code=303)
