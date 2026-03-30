from datetime import UTC, datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(
        default=None,
        sa_column=sa.Column(sa.BigInteger(), primary_key=True, autoincrement=True),
    )
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

    id: int | None = Field(
        default=None,
        sa_column=sa.Column(sa.BigInteger(), primary_key=True, autoincrement=True),
    )
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


class Screenshot(SQLModel, table=True):
    __tablename__ = "screenshots"

    id: int | None = Field(
        default=None,
        sa_column=sa.Column(sa.BigInteger(), primary_key=True, autoincrement=True),
    )
    annotation_id: int = Field(foreign_key="annotations.id", index=True)
    image_path: str = Field(max_length=1000)
    viewport_width: int = Field(default=1920)
    viewport_height: int = Field(default=1080)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False),
    )


class Action(SQLModel, table=True):
    __tablename__ = "actions"

    id: int | None = Field(
        default=None,
        sa_column=sa.Column(sa.BigInteger(), primary_key=True, autoincrement=True),
    )
    annotation_id: int = Field(foreign_key="annotations.id", index=True)
    screenshot_id: int | None = Field(default=None, foreign_key="screenshots.id")

    type: str  # click / scroll_up / scroll_down / type / stop
    click_axis_x: int | None = Field(default=None)
    click_axis_y: int | None = Field(default=None)
    input_text: str | None = Field(default=None)
    description: str
    final_result: str = Field(default="")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False),
    )
