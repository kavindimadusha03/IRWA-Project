from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=2, max_length=2000)
    history: List[Dict[str, str]] = Field(default_factory=list, max_length=8)


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=10, max_length=3000)


class AgentMessage(BaseModel):
    message_id: str = Field(min_length=1, max_length=100)
    request_id: str = Field(min_length=1, max_length=100)
    sender: str = Field(min_length=1, max_length=100)
    receiver: str = Field(min_length=1, max_length=100)
    task: str = Field(min_length=1, max_length=100)
    payload: Dict[str, Any]


class RetrievalItem(BaseModel):
    source_id: str
    title: str
    content: str
    category: str
    source_type: str
    bm25_score: float
    semantic_score: float
    hybrid_score: float
    status: str


class RetrievalResponse(BaseModel):
    query: str
    items: List[RetrievalItem]
    best_score: float
    decision: str


class TicketAnalysisResult(BaseModel):
    category: str
    canonical_issue: str
    entities: Dict[str, Optional[str]]
    masked_text: str


class ResolutionRequest(BaseModel):
    root_cause: str = Field(min_length=3, max_length=1000)
    resolution_notes: str = Field(min_length=5, max_length=3000)
    create_kb_draft: bool = True
