"""Initial schema: farmers, plots, recommendations, messages.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "farmers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), server_default=""),
        sa.Column("role", sa.String(32), server_default="farmer"),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("notify_opt_in", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("telegram_chat_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_farmers_email", "farmers", ["email"], unique=True)

    op.create_table(
        "plots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(64), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("farmers.id"), nullable=False),
        sa.Column("crop", sa.String(64), server_default="citrus"),
        sa.Column("stage", sa.String(64), server_default="fruit_growth"),
        sa.Column("irrigation_method", sa.String(32), server_default="drip"),
        sa.Column("area_ha", sa.Float(), server_default="0"),
        sa.Column("last_irrigation_on", sa.Date(), nullable=True),
        sa.Column("geom", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_plots_public_id", "plots", ["public_id"], unique=True)

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plot_id", sa.Integer(), sa.ForeignKey("plots.id"), nullable=False),
        sa.Column("engine_version", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("etc_mm", sa.Float(), nullable=True),
        sa.Column("gross_irrigation_mm", sa.Float(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_recommendations_plot_id", "recommendations", ["plot_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("farmer_id", sa.Integer(), sa.ForeignKey("farmers.id"), nullable=True),
        sa.Column("plot_id", sa.Integer(), sa.ForeignKey("plots.id"), nullable=True),
        sa.Column("channel", sa.String(32), server_default="web"),
        sa.Column("direction", sa.String(16), server_default="outbound"),
        sa.Column("body", sa.Text(), server_default=""),
        sa.Column("status", sa.String(32), server_default="queued"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_index("ix_recommendations_plot_id", table_name="recommendations")
    op.drop_table("recommendations")
    op.drop_index("ix_plots_public_id", table_name="plots")
    op.drop_table("plots")
    op.drop_index("ix_farmers_email", table_name="farmers")
    op.drop_table("farmers")
