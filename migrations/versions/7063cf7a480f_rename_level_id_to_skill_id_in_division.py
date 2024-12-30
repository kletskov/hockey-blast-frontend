"""Rename level_id to skill_id in Division

Revision ID: 7063cf7a480f
Revises: 343ede4fca2d
Create Date: 2024-12-11 13:04:38.883902

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7063cf7a480f'
down_revision = '343ede4fca2d'
branch_labels = None
depends_on = None


def upgrade():
    # Rename the column level_id to skill_id
    op.alter_column('divisions', 'level_id', new_column_name='skill_id')


def downgrade():
    # Revert the column name back to level_id
    op.alter_column('divisions', 'skill_id', new_column_name='level_id')
