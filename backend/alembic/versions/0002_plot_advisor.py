"""Link each plot to its assigned advisor."""
from alembic import op
import sqlalchemy as sa

revision = "0002_plot_advisor"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("plots") as batch:
        batch.add_column(sa.Column("advisor_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_plots_advisor", "farmers", ["advisor_id"], ["id"])
        batch.create_index("ix_plots_advisor_id", ["advisor_id"])


def downgrade():
    with op.batch_alter_table("plots") as batch:
        batch.drop_index("ix_plots_advisor_id")
        batch.drop_constraint("fk_plots_advisor", type_="foreignkey")
        batch.drop_column("advisor_id")
