"""initial

Revision ID: 2c68c5f5e1c2
Revises:
Create Date: 2026-03-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2c68c5f5e1c2"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("idx_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("idx_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "annotations",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("url", sa.String(length=4096), nullable=False),
        sa.Column("prompt", sa.String(), nullable=False),
        sa.Column("plan", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "screenshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("annotation_id", sa.Integer(), nullable=False),
        sa.Column("image_path", sa.String(length=1000), nullable=False),
        sa.Column("viewport_width", sa.Integer(), nullable=False),
        sa.Column("viewport_height", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["annotation_id"], ["annotations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_screenshots_annotation_id"), "screenshots", ["annotation_id"])

    op.create_table(
        "actions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("annotation_id", sa.BigInteger(), nullable=False),
        sa.Column("screenshot_id", sa.BigInteger(), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("click_axis_x", sa.Integer(), nullable=True),
        sa.Column("click_axis_y", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("final_result", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["annotation_id"], ["annotations.id"]),
        sa.ForeignKeyConstraint(["screenshot_id"], ["screenshots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("idx_actions_annotation_id"), "actions", ["annotation_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_screenshots_annotation_id"), table_name="screenshots")
    op.drop_table("annotations")
    op.drop_index(op.f("idx_users_username"), table_name="users")
    op.drop_index(op.f("idx_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_table("screenshots")
    op.drop_index(op.f("idx_actions_annotation_id"), table_name="actions")
    op.drop_table("actions")
