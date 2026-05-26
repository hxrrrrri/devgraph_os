"""add role column to users."""

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(50), nullable=False))
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    op.drop_column("users", "role")
