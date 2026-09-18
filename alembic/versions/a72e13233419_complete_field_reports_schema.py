
"""complete field reports schema

Revision ID: a72e13233419
Revises: 38e8889f5f2f
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a72e13233419"
down_revision: Union[str, Sequence[str], None] = "38e8889f5f2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "field_reports",
        sa.Column(
            "description_type",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )

    op.add_column(
        "field_reports",
        sa.Column(
            "ussd_info",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "field_reports",
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "COMPLETED",
                "ERROR",
                name="status_enum",
            ),
            nullable=False,
            server_default="PENDING",
        ),
    )

    op.alter_column(
        "field_reports",
        "captured_at",
        new_column_name="timestamp_captured",
    )

    op.alter_column(
        "field_reports",
        "synced_at",
        new_column_name="timestamp_synced",
    )

    op.execute(
        """
        ALTER TABLE field_reports
        ALTER COLUMN issue_type DROP DEFAULT
        """
    )

    op.execute(
        """
        ALTER TABLE field_reports
        ALTER COLUMN issue_type
        TYPE issue_type_enum
        USING (
            CASE issue_type::text
                WHEN 'land_degradation' THEN 'LAND_DEGRADATION'
                WHEN 'pest_outbreak' THEN 'PEST_OUTBREAK'
                WHEN 'crop_failure' THEN 'CROP_FAILURE'
            END
        )::issue_type_enum
        """
    )

    op.execute(
        """
        ALTER TABLE field_reports
        ALTER COLUMN sync_status DROP DEFAULT
        """
    )

    op.execute(
        """
        ALTER TABLE field_reports
        ALTER COLUMN sync_status
        TYPE sync_status_enum
        USING (
            CASE sync_status::text
                WHEN 'pending_sync' THEN 'PENDING_SYNC'
                WHEN 'synced' THEN 'SYNCED'
            END
        )::sync_status_enum
        """
    )

    op.execute(
        """
        ALTER TABLE field_reports
        ALTER COLUMN sync_status
        SET DEFAULT 'PENDING_SYNC'
        """
    )

    op.execute(
        """
        DROP TYPE issuetype
        """
    )

    op.execute(
        """
        DROP TYPE syncstatus
        """
    )

    op.alter_column(
        "field_reports",
        "description_type",
        server_default=None,
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE TYPE issuetype AS ENUM (
            'land_degradation',
            'pest_outbreak',
            'crop_failure'
        )
        """
    )

    op.execute(
        """
        CREATE TYPE syncstatus AS ENUM (
            'pending_sync',
            'synced'
        )
        """
    )

    op.execute(
        """
        ALTER TABLE field_reports
        ALTER COLUMN issue_type DROP DEFAULT
        """
    )

    op.execute(
        """
        ALTER TABLE field_reports
        ALTER COLUMN issue_type
        TYPE issuetype
        USING (
            CASE issue_type::text
                WHEN 'LAND_DEGRADATION' THEN 'land_degradation'
                WHEN 'PEST_OUTBREAK' THEN 'pest_outbreak'
                WHEN 'CROP_FAILURE' THEN 'crop_failure'
            END
        )::issuetype
        """
    )

    op.execute(
        """
        ALTER TABLE field_reports
        ALTER COLUMN sync_status DROP DEFAULT
        """
    )

    op.execute(
        """
        ALTER TABLE field_reports
        ALTER COLUMN sync_status
        TYPE syncstatus
        USING (
            CASE sync_status::text
                WHEN 'PENDING_SYNC' THEN 'pending_sync'
                WHEN 'SYNCED' THEN 'synced'
            END
        )::syncstatus
        """
    )

    op.execute(
        """
        ALTER TABLE field_reports
        ALTER COLUMN sync_status
        SET DEFAULT 'pending_sync'
        """
    )

    op.execute(
        """
        DROP TYPE issue_type_enum
        """
    )

    op.execute(
        """
        DROP TYPE sync_status_enum
        """
    )

    op.alter_column(
        "field_reports",
        "timestamp_captured",
        new_column_name="captured_at",
    )

    op.alter_column(
        "field_reports",
        "timestamp_synced",
        new_column_name="synced_at",
    )

    op.drop_column("field_reports", "status")
    op.drop_column("field_reports", "ussd_info")
    op.drop_column("field_reports", "description_type")

