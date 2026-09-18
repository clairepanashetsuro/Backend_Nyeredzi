"""add details to field reports

Revision ID: 38e8889f5f2f
Revises: f1ed14b1cb5b
Create Date: 2026-09-18 16:15:02.883434
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "38e8889f5f2f"
down_revision: Union[str, Sequence[str], None] = "f1ed14b1cb5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "field_reports",
        sa.Column("details", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("field_reports", "details")