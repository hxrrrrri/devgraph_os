"""init users + posts."""

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
    )
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
    )
    op.create_index("ix_posts_user_id", "posts", ["user_id"])


def downgrade() -> None:
    op.drop_table("posts")
    op.drop_table("users")
