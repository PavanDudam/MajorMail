# app/db_models.py

from typing import List, Optional
from datetime import datetime
from sqlmodel import Field, Relationship, SQLModel, Column, TEXT
from sqlalchemy import TIMESTAMP

class UserToken(SQLModel, table=True):
    """Stores user's OAuth tokens, linked to a User."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    access_token: str
    refresh_token: Optional[str] = None
    user: "User" = Relationship(back_populates="tokens")


class Email(SQLModel, table=True):
    """Stores individual emails, linked to a User."""
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")
    
    message_id: str = Field(unique=True, index=True)
    subject: Optional[str] = None
    sender: Optional[str] = None
    
    # --- THE FIX: Added the 'body' column ---
    # We use Column(TEXT) for potentially long email bodies.
    body: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    # ----------------------------------------

    summary: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    category: str = Field(default="Uncategorized", index=True)
    priority_score: int = Field(default=0, index=True)
    suggested_action : Optional[str] = Field(default=None, index=True)
    received_at: Optional[datetime] = Field(
        default=None, sa_column=Column(TIMESTAMP(timezone=True))
    )
    
    owner: "User" = Relationship(back_populates="emails")


class User(SQLModel, table=True):
    """Represents a user of the application."""
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: Optional[str] = None
    
    tokens: List[UserToken] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    emails: List[Email] = Relationship(back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class EmailRead(SQLModel):
    """
    This model defines the data structure for an email when it's sent
    from the API to the client. It excludes sensitive or unnecessary fields.
    """
    id: int
    subject: Optional[str]
    sender: Optional[str]
    summary: Optional[str]
    category: str
    priority_score: int
    received_at: Optional[datetime]
    suggested_action : Optional[str]

class SenderDossier(SQLModel):
    """
    This model defines the data structure for the sender dossier response.
    """
    total_emails: int
    category_counts: dict[str, int]
    # We can add more fields later, like 'latest_email_summary'
    average_priority_score: float
    latest_email_summary: Optional[str]
    most_common_action: Optional[str]
