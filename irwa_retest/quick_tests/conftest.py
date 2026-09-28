"""Safety boundary: set isolation BEFORE any application imports during collection."""
import os
import tempfile

_SANDBOX = tempfile.TemporaryDirectory(prefix='irwa-quick-tests-')
os.environ['DATABASE_URL'] = 'sqlite:///' + _SANDBOX.name.replace('\\', '/') + '/test.sqlite'
os.environ['GROQ_API_KEY'] = ''  # quick tests never send prompts or credentials to a provider
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'

import pytest

@pytest.fixture(autouse=True)
def no_live_llm(monkeypatch):
    from app.services.llm import llm
    monkeypatch.setattr(llm, 'enabled', False)
    monkeypatch.setattr(llm, 'chat', lambda *_a, **_kw: '')
    monkeypatch.setattr(llm, 'chat_json', lambda *_a, **_kw: {})

@pytest.fixture
def isolated_session():
    """Completely separate in-memory SQLModel DB; never use app.database.engine."""
    from sqlalchemy.pool import StaticPool
    from sqlmodel import SQLModel, Session, create_engine
    import app.models  # register all project tables
    eng = create_engine('sqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    with Session(eng) as session:
        yield session
    eng.dispose()

@pytest.fixture
def web_client(isolated_session):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from fastapi.staticfiles import StaticFiles
    from pathlib import Path
    from app.database import get_session
    from app.routes import agents, admin, knowledge
    import app
    web = FastAPI()
    project_root = Path(__file__).resolve().parents[2]
    static_dir = project_root / "app" / "static"
    web.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    web.include_router(agents.router)
    web.include_router(admin.router)
    web.include_router(knowledge.router)
    def get_isolated_session():
        yield isolated_session
    web.dependency_overrides[get_session] = get_isolated_session
    with TestClient(web,raise_server_exceptions=False,follow_redirects=False) as client:
        yield client

@pytest.fixture
def actor(isolated_session):
    from app.models import User
    from app.services.auth import create_access_token
    def new(role='CUSTOMER'):
        name='irquick_'+role.lower()+'_'+str(len(isolated_session.new)+len(isolated_session.identity_map))
        u=User(username=name,full_name='IR Quick Synthetic',role=role,hashed_password='not-used')
        isolated_session.add(u); isolated_session.commit(); isolated_session.refresh(u)
        token=create_access_token(u.id,u.username,u.role)
        return u,token
    return new
