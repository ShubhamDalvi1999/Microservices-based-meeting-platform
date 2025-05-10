"""Add guest_user_id column to chat_messages

Revision ID: 8d345c62a982
Revises: 7f452a69c018
Create Date: 2025-05-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8d345c62a982'
down_revision = '7f452a69c018'
branch_labels = None
depends_on = None


def upgrade():
    # Add guest_user_id column to chat_messages table
    op.add_column('chat_messages', sa.Column('guest_user_id', sa.String(255), nullable=True), schema='chat')
    
    # Make user_id column nullable
    op.alter_column('chat_messages', 'user_id', nullable=True, schema='chat')


def downgrade():
    # Make user_id column not nullable again
    op.alter_column('chat_messages', 'user_id', nullable=False, schema='chat')
    
    # Remove guest_user_id column from chat_messages table
    op.drop_column('chat_messages', 'guest_user_id', schema='chat') 