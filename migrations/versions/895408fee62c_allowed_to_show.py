"""allowed_to_show

Revision ID: 895408fee62c
Revises: 7716af9f055d
Create Date: 2026-08-01 00:28:18.594076

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '895408fee62c'
down_revision = '7716af9f055d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('allowed_to_show', sa.Boolean(), nullable=False, server_default=sa.text('true'))
        )


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('allowed_to_show')