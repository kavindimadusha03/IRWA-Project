from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.database import get_session
from app.models import PasswordResetToken, User
from app.services.auth import create_access_token, decode_access_token, hash_password, verify_password

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def _template_context(request: Request, **values):
    return {"request": request, **values}


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def current_user_from_request(request: Request, session: Session):
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        return None
    return session.get(User, user_id)


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", _template_context(request))


@router.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    session: Session = Depends(get_session),
):
    username = username.strip().lower()
    full_name = full_name.strip()
    error = None
    if len(username) < 3 or len(username) > 50 or not username.replace("_", "").replace("-", "").isalnum():
        error = "Use 3-50 letters, numbers, hyphens, or underscores for your username."
    elif len(full_name) < 2 or len(full_name) > 120:
        error = "Enter a name between 2 and 120 characters."
    elif len(password) < 8:
        error = "Your password must contain at least 8 characters."
    elif password != confirm_password:
        error = "The passwords do not match."
    elif session.exec(select(User).where(User.username == username)).first():
        error = "That username is already in use."
    if error:
        return templates.TemplateResponse(
            "register.html",
            _template_context(request, error=error, username=username, full_name=full_name),
            status_code=400,
        )

    user = User(username=username, full_name=full_name, hashed_password=hash_password(password), role="CUSTOMER")
    session.add(user)
    session.commit()
    return RedirectResponse(url="/?registered=1", status_code=303)


@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", _template_context(request))


@router.post("/forgot-password", response_class=HTMLResponse)
def forgot_password(
    request: Request,
    username: str = Form(...),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.username == username.strip().lower())).first()
    reset_url = None
    if user:
        raw_token = secrets.token_urlsafe(32)
        session.add(PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_reset_token(raw_token),
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30),
        ))
        session.commit()
        reset_url = f"/reset-password?token={raw_token}"
    return templates.TemplateResponse(
        "forgot_password.html",
        _template_context(request, submitted=True, reset_url=reset_url),
    )


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request, token: str = ""):
    return templates.TemplateResponse("reset_password.html", _template_context(request, token=token))


@router.post("/reset-password")
def reset_password(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    session: Session = Depends(get_session),
):
    token_record = session.exec(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash_reset_token(token))
    ).first()
    now = datetime.utcnow()
    error = None
    if not token_record or token_record.used_at or token_record.expires_at < now:
        error = "This reset link is invalid or expired."
    elif len(password) < 8:
        error = "Your password must contain at least 8 characters."
    elif password != confirm_password:
        error = "The passwords do not match."
    if error:
        return templates.TemplateResponse(
            "reset_password.html",
            _template_context(request, token=token, error=error),
            status_code=400,
        )
    user = session.get(User, token_record.user_id)
    user.hashed_password = hash_password(password)
    token_record.used_at = now
    session.add(user)
    session.add(token_record)
    session.commit()
    return RedirectResponse(url="/?reset=1", status_code=303)


@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, session: Session = Depends(get_session)):
    user = current_user_from_request(request, session)
    if not user:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("profile.html", _template_context(request, user=user))


@router.post("/profile")
def update_profile(
    request: Request,
    full_name: str = Form(...),
    current_password: str = Form(""),
    new_password: str = Form(""),
    confirm_password: str = Form(""),
    session: Session = Depends(get_session),
):
    user = current_user_from_request(request, session)
    if not user:
        return RedirectResponse(url="/", status_code=303)
    full_name = full_name.strip()
    error = None
    if len(full_name) < 2 or len(full_name) > 120:
        error = "Enter a name between 2 and 120 characters."
    elif new_password and not verify_password(current_password, user.hashed_password):
        error = "Your current password is incorrect."
    elif new_password and len(new_password) < 8:
        error = "Your new password must contain at least 8 characters."
    elif new_password != confirm_password:
        error = "The new passwords do not match."
    if error:
        return templates.TemplateResponse("profile.html", _template_context(request, user=user, error=error), status_code=400)
    user.full_name = full_name
    if new_password:
        user.hashed_password = hash_password(new_password)
    session.add(user)
    session.commit()
    return RedirectResponse(url="/profile?updated=1", status_code=303)


@router.post("/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.username == username)).first()
    if not user or not user.is_active or not verify_password(password, user.hashed_password):
        return RedirectResponse(url="/?error=1", status_code=303)
    token = create_access_token(user.id, user.username, user.role)
    response = RedirectResponse(url="/home", status_code=303)
    response.set_cookie("access_token", token, httponly=True, samesite="lax")
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response
