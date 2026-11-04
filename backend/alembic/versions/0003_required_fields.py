"""Align required-column constraints with the ORM without inventing data.

Existing NULLs must be corrected by the database owner before this migration.
PostgreSQL applies these changes transactionally, leaving the schema unchanged
if any required column contains NULL.
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_required_fields"
down_revision = "0002_plot_advisor"
branch_labels = None
depends_on = None

FIELDS = {
    "farmers": {"full_name": sa.String(255), "role": sa.String(32), "notify_opt_in": sa.Boolean()},
    "plots": {"crop": sa.String(64), "stage": sa.String(64), "irrigation_method": sa.String(32), "area_ha": sa.Float()},
    "messages": {"channel": sa.String(32), "direction": sa.String(16), "body": sa.Text(), "status": sa.String(32)},
    "recommendations": {},
}


def set_nullable(nullable):
    for table, fields in FIELDS.items():
        with op.batch_alter_table(table) as batch:
            for name, kind in {**fields, "created_at": sa.DateTime(timezone=True)}.items():
                batch.alter_column(name, existing_type=kind, nullable=nullable)


def upgrade():
    set_nullable(False)


def downgrade():
    set_nullable(True)
