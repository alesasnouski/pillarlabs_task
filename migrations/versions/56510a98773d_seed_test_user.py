"""seed_test_user

Revision ID: 56510a98773d
Revises: 2c68c5f5e1c2
Create Date: 2026-03-30 20:11:13.501696

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "56510a98773d"
down_revision: str | None = "2c68c5f5e1c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from app.core.security import hash_password

    hashed = hash_password("secret")
    # TODO: fast and dirty, make fixture for base users
    op.execute(
        f"""
        INSERT INTO users (username, email, hashed_password, is_active, created_at, updated_at) 
        SELECT 'test', 'test@example.com', '{hashed}', true, NOW(), NOW()
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'test@example.com');
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM users WHERE email = 'test@example.com';")
