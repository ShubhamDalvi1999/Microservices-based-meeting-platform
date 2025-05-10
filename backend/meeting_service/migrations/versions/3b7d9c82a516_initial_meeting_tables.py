"""Initial meeting tables

Revision ID: 3b7d9c82a516
Revises: 
Create Date: 2023-07-10 10:53:12.123456

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3b7d9c82a516'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Only import pre-existing tables that already created in init_db.sql
    pass


def downgrade():
    # Don't drop anything - this is initial migration
    pass 