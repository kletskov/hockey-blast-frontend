"""add org to LevelsMonthly

Revision ID: 9bfd97dfccf4
Revises: f490138b9259
Create Date: 2024-12-11 12:23:07.235915

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9bfd97dfccf4'
down_revision = 'f490138b9259'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('levels_monthly', schema=None) as batch_op:
        batch_op.add_column(sa.Column('org_id', sa.Integer(), nullable=True))
        batch_op.drop_constraint('_year_month_league_season_level_uc', type_='unique')
        batch_op.create_unique_constraint('_org_year_month_league_season_level_uc', ['org_id', 'year', 'month', 'league_number', 'season_number', 'level'])
        batch_op.create_foreign_key(None, 'organizations', ['org_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('levels_monthly', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint('_org_year_month_league_season_level_uc', type_='unique')
        batch_op.create_unique_constraint('_year_month_league_season_level_uc', ['year', 'month', 'league_number', 'season_number', 'level'])
        batch_op.drop_column('org_id')

    # ### end Alembic commands ###
