"""DivisionStatsSkater and DivisionStatsSkater

Revision ID: 7cc11e8eec68
Revises: 8386a3554f0f
Create Date: 2024-12-22 15:54:13.854427

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7cc11e8eec68'
down_revision = '8386a3554f0f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('division_stats_skater',
    sa.Column('division_id', sa.Integer(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('human_id', sa.Integer(), nullable=False),
    sa.Column('games_played', sa.Integer(), nullable=True),
    sa.Column('goals', sa.Integer(), nullable=True),
    sa.Column('assists', sa.Integer(), nullable=True),
    sa.Column('points', sa.Integer(), nullable=True),
    sa.Column('penalties', sa.Integer(), nullable=True),
    sa.Column('goals_per_game', sa.Float(), nullable=True),
    sa.Column('points_per_game', sa.Float(), nullable=True),
    sa.Column('assists_per_game', sa.Float(), nullable=True),
    sa.Column('penalties_per_game', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['division_id'], ['divisions.id'], ),
    sa.ForeignKeyConstraint(['human_id'], ['humans.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('human_id', 'division_id', name='_human_division_uc_skater1')
    )
    with op.batch_alter_table('division_stats_skater', schema=None) as batch_op:
        batch_op.create_index('idx_division_assists_per_game3', ['division_id', 'assists_per_game'], unique=False)
        batch_op.create_index('idx_division_games_played3', ['division_id', 'games_played'], unique=False)
        batch_op.create_index('idx_division_goals_per_game3', ['division_id', 'goals_per_game'], unique=False)
        batch_op.create_index('idx_division_penalties_per_game3', ['division_id', 'penalties_per_game'], unique=False)
        batch_op.create_index('idx_division_points_per_game3', ['division_id', 'points_per_game'], unique=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('division_stats_skater', schema=None) as batch_op:
        batch_op.drop_index('idx_division_points_per_game3')
        batch_op.drop_index('idx_division_penalties_per_game3')
        batch_op.drop_index('idx_division_goals_per_game3')
        batch_op.drop_index('idx_division_games_played3')
        batch_op.drop_index('idx_division_assists_per_game3')

    op.drop_table('division_stats_skater')
    # ### end Alembic commands ###
