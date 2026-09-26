from functools import lru_cache
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "KnowGap AI")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./knowgap.db")
    hybrid_bm25_weight: float = float(os.getenv("HYBRID_BM25_WEIGHT", "0.45"))
    hybrid_semantic_weight: float = float(os.getenv("HYBRID_SEMANTIC_WEIGHT", "0.55"))
    high_confidence_threshold: float = float(os.getenv("HIGH_CONFIDENCE_THRESHOLD", "0.68"))
    uncertain_threshold: float = float(os.getenv("UNCERTAIN_THRESHOLD", "0.55"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
