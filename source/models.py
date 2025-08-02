from enum import unique
from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

class UserToken(SQLModel, table=True):
    id:Optional[int] = Field(default=None,primary_key=True)
    user_id:int = Field(foreign_key="user.id")
    access_token:str = Field(index=True)
    refresh_token:Optional[str] = None
    user : "User" = Relationship(back_populates="tokens")


class Email(SQLModel, table=True):
    id:Optional[int] = Field(default=None,primary_key=True)
    owner_id:int = Field(foreign_key="user.id")
    message_id:str = Field(unique=True, index=True)
    subject:Optional[str] = None
    sender:Optional[str] = None
    summary:Optional[str] = None
    category:str = Field(default="Uncategorized", index=True)
    priority_score :int = Field(default=0, index=True)
    owner:"User"= Relationship(back_populates="emails")


class User(SQLModel, table=True):
    id:Optional[int] = Field(default=None,primary_key=True)
    email:str = Field(unique=True, index=True)
    full_name:Optional[str] = None
    tokens : List[UserToken] = Relationship(back_populates="user")
    emails :List[Email] = Relationship(back_populates="owner")