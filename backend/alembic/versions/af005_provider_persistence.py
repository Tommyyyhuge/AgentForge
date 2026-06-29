"""add provider persistence tables

Revision ID: af005_provider_persistence
Revises: bc6b0a0c24d3
Create Date: 2026-06-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "af005_provider_persistence"
down_revision: Union[str, None] = "bc6b0a0c24d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provider_configs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("provider_type", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=True),
        sa.Column("auth_type", sa.String(), nullable=False),
        sa.Column("api_key_id", sa.String(), nullable=True),
        sa.Column("default_model", sa.String(), nullable=True),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("rate_limit_policy", sa.JSON(), nullable=False),
        sa.Column("streaming_enabled", sa.Boolean(), nullable=False),
        sa.Column("tool_calling_enabled", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_provider_configs_provider_type"),
        "provider_configs",
        ["provider_type"],
        unique=False,
    )

    op.create_table(
        "model_configs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("provider_id", sa.String(), nullable=False),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("context_window", sa.Integer(), nullable=True),
        sa.Column("supports_streaming", sa.Boolean(), nullable=True),
        sa.Column("supports_tool_calling", sa.Boolean(), nullable=True),
        sa.Column("supports_json_mode", sa.Boolean(), nullable=True),
        sa.Column("supports_vision", sa.Boolean(), nullable=True),
        sa.Column("supports_embeddings", sa.Boolean(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_configs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_model_configs_provider_id"),
        "model_configs",
        ["provider_id"],
        unique=False,
    )

    op.create_table(
        "provider_health_checks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("provider_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("checked_at", sa.DateTime(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("model_tested", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_configs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_provider_health_checks_provider_id"),
        "provider_health_checks",
        ["provider_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_provider_health_checks_provider_id"),
        table_name="provider_health_checks",
    )
    op.drop_table("provider_health_checks")
    op.drop_index(op.f("ix_model_configs_provider_id"), table_name="model_configs")
    op.drop_table("model_configs")
    op.drop_index(
        op.f("ix_provider_configs_provider_type"), table_name="provider_configs"
    )
    op.drop_table("provider_configs")
