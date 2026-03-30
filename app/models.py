from datetime import UTC, datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, sa_column=sa.Column(sa.BigInteger(), primary_key=True, autoincrement=True))
    username: str = Field(max_length=150, unique=True, index=True)
    email: str = Field(max_length=254, unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False),
    )


class Annotation(SQLModel, table=True):
    __tablename__ = "annotations"

    id: int | None = Field(default=None, sa_column=sa.Column(sa.BigInteger(), primary_key=True, autoincrement=True))
    user_id: int = Field(foreign_key="users.id")
    url: str = Field(max_length=4096)
    prompt: str
    plan: str = Field(default="")
    status: str = Field(default="created")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False),
    )
