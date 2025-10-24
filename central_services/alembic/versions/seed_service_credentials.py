"""seed service credentials

Revision ID: seed_service_credentials
Revises: c557cdfff56c
Create Date: 2025-10-23

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import column, table

# revision identifiers, used by Alembic.
revision: str = 'seed_service_credentials'
down_revision: str | None = 'c557cdfff56c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Define table structure for insert
service_credentials = table('service_credentials',
    column('service_name', sa.String),
    column('service_secret', sa.String),
    column('role', sa.String),
)

def upgrade() -> None:
    # Initial service credentials
    op.bulk_insert(service_credentials, [
        {
            'service_name': 'inventory-service',
            'service_secret': 'qlDKAOp65mSGgtNNjMVRZO1bBPgDS5ArhZYc+YF1cjA=',  # Replace in production
            'role': 'store'
        },
        {
            'service_name': 'order-service',
            'service_secret': 'ZJwzHrsaeQBckoBpMmrIoyiVJlSI+DJLfb5yt2wVtVo=',  # Replace in production
            'role': 'store'
        },
    ])

def downgrade() -> None:
    op.execute(
        service_credentials.delete().where(
            service_credentials.c.service_name.in_([
                'inventory-service',
                'order-service',
                'admin-service'
            ])
        )
    )