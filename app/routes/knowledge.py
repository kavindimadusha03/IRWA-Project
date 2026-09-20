from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session
from app.database import get_session
from app.models import KnowledgeArticle
from app.routes.auth import current_user_from_request

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/{article_id}/approve")
def approve_article(article_id: int, request: Request, session: Session = Depends(get_session)):
    user = current_user_from_request(request, session)
    if not user or user.role not in {"KNOWLEDGE_ANALYST", "ADMIN"}:
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
