from datetime import datetime
from pathlib import Path
import re
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session
from app.models import Category, KnowledgeArticle, PasswordResetToken, Ticket, User
from app.routes.auth import current_user_from_request
from app.services.auth import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))

ROLES = ("CUSTOMER", "IT_SUPPORT", "KNOWLEDGE_ANALYST", "ADMIN")
DEFAULT_CATEGORIES = (
    "Wi-Fi / DNS",
    "VPN",
    "Outlook / MFA",
    "Accounts / Passwords",
    "Printers",
    "Windows / Updates",
    "Software Installation",
    "Remote Desktop",
)


def _admin_user(request: Request, session: Session):
    user = current_user_from_request(request, session)
    if not user or user.role != "ADMIN":
        return None
    return user


def _redirect(message: str = "", error: str = ""):
    params = []
    if message:
        params.append(f"message={quote_plus(message)}")
    if error:
        params.append(f"error={quote_plus(error)}")
    suffix = f"?{'&'.join(params)}" if params else ""
    return RedirectResponse(url=f"/admin{suffix}", status_code=303)


def _ensure_categories(session: Session):
    existing = {category.name for category in session.exec(select(Category)).all()}
    article_names = {article.category for article in session.exec(select(KnowledgeArticle)).all() if article.category}
    ticket_names = {ticket.category for ticket in session.exec(select(Ticket)).all() if ticket.category and ticket.category != "Unknown"}
    names = set(DEFAULT_CATEGORIES) | article_names | ticket_names
    for name in sorted(names - existing):
        session.add(Category(name=name))
    if names - existing:
        session.commit()


def _article_by_doc_id(session: Session, doc_id: str, exclude_id: int | None = None):
    article = session.exec(select(KnowledgeArticle).where(KnowledgeArticle.doc_id == doc_id)).first()
    if article and article.id != exclude_id:
        return article
    return None


def _next_article_doc_id(session: Session):
    numeric_ids = [
        int(match.group(1))
        for article in session.exec(select(KnowledgeArticle)).all()
        if (match := re.fullmatch(r"KB-(\d+)", article.doc_id))
    ]
    return f"KB-{max(numeric_ids, default=0) + 1:03d}"


@router.get("", response_class=HTMLResponse)
def admin_page(request: Request, session: Session = Depends(get_session)):
    user = _admin_user(request, session)
    if not user:
        return HTMLResponse("Admin access required", status_code=403)
    _ensure_categories(session)
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "user": user,
            "users": session.exec(select(User).order_by(User.username)).all(),
            "articles": session.exec(select(KnowledgeArticle).order_by(KnowledgeArticle.updated_at.desc())).all(),
            "categories": session.exec(select(Category).order_by(Category.name)).all(),
            "next_article_doc_id": _next_article_doc_id(session),
            "roles": ROLES,
            "message": request.query_params.get("message"),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/users/create")
def create_user(
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    session: Session = Depends(get_session),
):
    if not _admin_user(request, session):
        return HTMLResponse("Admin access required", status_code=403)
    username = username.strip().lower()
    full_name = full_name.strip()
    if role not in ROLES:
        return _redirect(error="Select a valid role.")
    if len(username) < 3 or not username.replace("_", "").replace("-", "").isalnum():
        return _redirect(error="Use a valid username with letters, numbers, hyphens, or underscores.")
    if len(full_name) < 2 or len(password) < 8:
        return _redirect(error="Full name and an 8-character password are required.")
    if session.exec(select(User).where(User.username == username)).first():
        return _redirect(error="That username is already in use.")
    session.add(User(username=username, full_name=full_name, hashed_password=hash_password(password), role=role))
    session.commit()
    return _redirect(message="User created.")


@router.post("/users/{user_id}")
def update_user(
    user_id: int,
    request: Request,
    full_name: str = Form(...),
    role: str = Form(...),
    is_active: bool = Form(False),
    session: Session = Depends(get_session),
):
    admin = _admin_user(request, session)
    if not admin:
        return HTMLResponse("Admin access required", status_code=403)
    target = session.get(User, user_id)
    if not target:
        return _redirect(error="User not found.")
    if role not in ROLES or len(full_name.strip()) < 2:
        return _redirect(error="Enter a valid name and role.")
    target.full_name = full_name.strip()
    target.role = role
    target.is_active = is_active
    session.add(target)
    session.commit()
    return _redirect(message=f"Updated {target.username}.")


@router.post("/users/{user_id}/delete")
def delete_user(user_id: int, request: Request, session: Session = Depends(get_session)):
    admin = _admin_user(request, session)
    if not admin:
        return HTMLResponse("Admin access required", status_code=403)
    target = session.get(User, user_id)
    if not target:
        return _redirect(error="User not found.")
    if target.id == admin.id:
        return _redirect(error="You cannot delete your own admin account.")
    if session.exec(select(Ticket).where(Ticket.user_id == target.id)).first():
        return _redirect(error="This user owns tickets and cannot be deleted. Deactivate the account instead.")
    for reset_token in session.exec(select(PasswordResetToken).where(PasswordResetToken.user_id == target.id)).all():
        session.delete(reset_token)
    session.delete(target)
    session.commit()
    return _redirect(message=f"Deleted {target.username}.")


@router.post("/articles/create")
def create_article(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    category: str = Form(...),
    status: str = Form("draft"),
    supported_os: str = Form("Any"),
    session: Session = Depends(get_session),
):
    admin = _admin_user(request, session)
    if not admin:
        return HTMLResponse("Admin access required", status_code=403)
    title, content, category = title.strip(), content.strip(), category.strip()
    if not title or not content or not category:
        return _redirect(error="Title, content, and category are required.")
    doc_id = _next_article_doc_id(session)
    session.add(KnowledgeArticle(
        doc_id=doc_id,
        title=title,
        content=content,
        category=category,
        status="draft",
        authoritative=False,
        author=admin.username,
        supported_os=supported_os.strip() or "Any",
    ))
    session.commit()
    return _redirect(message=f"Knowledge article {doc_id} created as a draft for analyst approval.")


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
    return HTMLResponse("Knowledge article editing is restricted to Knowledge Analysts", status_code=403)


@router.post("/articles/{article_id}/delete")
def delete_article(article_id: int, request: Request, session: Session = Depends(get_session)):
    return HTMLResponse("Knowledge article editing is restricted to Knowledge Analysts", status_code=403)


@router.post("/categories/create")
def create_category(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    session: Session = Depends(get_session),
):
    if not _admin_user(request, session):
        return HTMLResponse("Admin access required", status_code=403)
    name = name.strip()
    if len(name) < 2:
        return _redirect(error="Category name must contain at least 2 characters.")
    if session.exec(select(Category).where(Category.name == name)).first():
        return _redirect(error="That category already exists.")
    session.add(Category(name=name, description=description.strip()))
    session.commit()
    return _redirect(message="Category created.")


@router.post("/categories/{category_id}")
def update_category(
    category_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    is_active: bool = Form(False),
    session: Session = Depends(get_session),
):
    if not _admin_user(request, session):
        return HTMLResponse("Admin access required", status_code=403)
    category = session.get(Category, category_id)
    if not category or len(name.strip()) < 2:
        return _redirect(error="Category not found or invalid.")
    duplicate = session.exec(select(Category).where(Category.name == name.strip())).first()
    if duplicate and duplicate.id != category.id:
        return _redirect(error="That category already exists.")
    category.name = name.strip()
    category.description = description.strip()
    category.is_active = is_active
    session.add(category)
    session.commit()
    return _redirect(message="Category updated.")


@router.post("/categories/{category_id}/delete")
def delete_category(category_id: int, request: Request, session: Session = Depends(get_session)):
    if not _admin_user(request, session):
        return HTMLResponse("Admin access required", status_code=403)
    category = session.get(Category, category_id)
    if not category:
        return _redirect(error="Category not found.")
    if session.exec(select(KnowledgeArticle).where(KnowledgeArticle.category == category.name)).first():
        return _redirect(error="This category is used by an article. Deactivate it instead.")
    session.delete(category)
    session.commit()
    return _redirect(message="Category deleted.")
