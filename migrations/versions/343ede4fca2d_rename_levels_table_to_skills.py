"""Rename levels table to skills.

Revision ID: 343ede4fca2d
Revises: 112494871c38
Create Date: 2024-12-11 12:59:57.451726

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '343ede4fca2d'
down_revision = '112494871c38'
branch_labels = None
depends_on = None


def upgrade():
    # Rename the levels table to skills
    op.rename_table('levels', 'skills')


def downgrade():
    # Revert the table name back to levels
    op.rename_table('skills', 'levels')
