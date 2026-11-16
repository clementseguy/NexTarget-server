"""add persisted Coach sessions and analyses

Revision ID: d4f2a1c87b90
Revises: 8e27c4a91f62
Create Date: 2026-09-11 20:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f2a1c87b90"
down_revision: Union[str, None] = "8e27c4a91f62"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "coach_session",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("client_session_id", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "client_session_id",
            name="uix_coach_session_user_client",
        ),
    )
    op.create_index(
        op.f("ix_coach_session_user_id"),
        "coach_session",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_coach_session_client_session_id"),
        "coach_session",
        ["client_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_coach_session_content_hash"),
        "coach_session",
        ["content_hash"],
        unique=False,
    )
    op.create_table(
        "coach_session_analysis",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("coach_session_id", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("contract_version", sa.Integer(), nullable=False),
        sa.Column("prompt_variant", sa.String(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["coach_session_id"], ["coach_session.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "coach_session_id",
            "content_hash",
            "contract_version",
            "prompt_variant",
            name="uix_coach_analysis_idempotency",
        ),
    )
    op.create_index(
        op.f("ix_coach_session_analysis_coach_session_id"),
        "coach_session_analysis",
        ["coach_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_coach_session_analysis_content_hash"),
        "coach_session_analysis",
        ["content_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_coach_session_analysis_content_hash"),
        table_name="coach_session_analysis",
    )
    op.drop_index(
        op.f("ix_coach_session_analysis_coach_session_id"),
        table_name="coach_session_analysis",
    )
    op.drop_table("coach_session_analysis")
    op.drop_index(op.f("ix_coach_session_content_hash"), table_name="coach_session")
    op.drop_index(
        op.f("ix_coach_session_client_session_id"), table_name="coach_session"
    )
    op.drop_index(op.f("ix_coach_session_user_id"), table_name="coach_session")
    op.drop_table("coach_session")
