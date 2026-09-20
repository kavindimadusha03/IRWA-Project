from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    full_name: str
    hashed_password: str
    role: str = Field(index=True)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PasswordResetToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    token_hash: str = Field(index=True, unique=True)
    expires_at: datetime
    used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Ticket(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_code: str = Field(index=True, unique=True)
    user_id: int = Field(foreign_key="user.id")
    title: str
    description: str
    masked_description: str = ""
    category: str = "Unknown"
    priority: str = "Medium"
    canonical_issue: str = ""
    status: str = Field(default="OPEN", index=True)
    approval_status: str = Field(default="PENDING", index=True)
    approved_by: Optional[int] = Field(default=None, foreign_key="user.id")
    approved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_to: Optional[int] = Field(default=None, foreign_key="user.id")
    root_cause: str = ""
    resolution_notes: str = ""
    retrieval_confidence: float = 0.0
    source_used: str = ""
    recommended_solution: str = ""
    decision_explanation: str = ""
    suggested_reply: str = ""
    history_summary: str = ""
    learning_summary: str = ""
    solved_by_user: bool = False


class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    ticket_id: Optional[int] = Field(default=None, foreign_key="ticket.id", index=True)
    title: str
    message: str
    notification_type: str = Field(default="ticket_resolved", index=True)
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SolutionFeedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    rating: str = Field(index=True)
    comment: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TicketCitation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id", index=True)
    source_id: str = Field(index=True)
    title: str
    category: str = "Unknown"
    source_type: str = "internal_kb"
    relevance_score: float = 0.0
    rank: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeArticle(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    doc_id: str = Field(index=True, unique=True)
    title: str
    content: str
    category: str = Field(index=True)
    status: str = Field(default="approved", index=True)
    source_type: str = "internal_kb"
    author: str = "system"
    authoritative: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    supported_os: str = "Any"
    security_class: str = "internal"


class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: str = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: str = Field(index=True)
    message_id: str = Field(index=True)
    sender: str
    receiver: str
    task: str
    payload_summary: str
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SecurityEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: str = Field(index=True)
    event_type: str
    severity: str
    details: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
