"""level instead of level_id in Division as unique

Revision ID: fde4ebac8df2
Revises: 8c54d9f4da79
Create Date: 2024-12-11 12:47:13.693412

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fde4ebac8df2'
down_revision = '8c54d9f4da79'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('divisions', schema=None) as batch_op:
        batch_op.drop_constraint('_org_league_season_level_uc', type_='unique')
        batch_op.create_unique_constraint('_org_league_season_level_uc', ['org_id', 'league_number', 'season_number', 'level'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('divisions', schema=None) as batch_op:
        batch_op.drop_constraint('_org_league_season_level_uc', type_='unique')
        batch_op.create_unique_constraint('_org_league_season_level_uc', ['org_id', 'league_number', 'season_number', 'level_id'])

    # ### end Alembic commands ###
