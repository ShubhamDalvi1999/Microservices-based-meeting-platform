"""Add guest_owner_id column

Revision ID: 62a8f4b9d712
Revises: 3b7d9c82a516
Create Date: 2023-07-12 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '62a8f4b9d712'
down_revision = '3b7d9c82a516'
branch_labels = None
depends_on = None


def upgrade():
    # Add guest_owner_id column to meetings table
    op.add_column('meetings', sa.Column('guest_owner_id', sa.String(255), nullable=True), schema='meetings')


def downgrade():
    # Remove guest_owner_id column from meetings table
    op.drop_column('meetings', 'guest_owner_id', schema='meetings') 