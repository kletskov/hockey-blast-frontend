"""rename tables to start with org_stats

Revision ID: d0754f1837ac
Revises: dbde5306c617
Create Date: 2024-12-22 15:16:05.647529

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd0754f1837ac'
down_revision = 'dbde5306c617'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('org_stats_goalie',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('human_id', sa.Integer(), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('games_played', sa.Integer(), nullable=True),
    sa.Column('goals_allowed', sa.Integer(), nullable=True),
    sa.Column('goals_allowed_per_game', sa.Float(), nullable=True),
    sa.Column('shots_faced', sa.Integer(), nullable=True),
    sa.Column('save_percentage', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['human_id'], ['humans.id'], ),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('human_id', 'org_id', name='_human_org_uc_goalie1')
    )
    with op.batch_alter_table('org_stats_goalie', schema=None) as batch_op:
        batch_op.create_index('idx_org_games_played_goalie1', ['org_id', 'games_played'], unique=False)
        batch_op.create_index('idx_org_goals_allowed1', ['org_id', 'goals_allowed'], unique=False)
        batch_op.create_index('idx_org_goals_allowed_per_game1', ['org_id', 'goals_allowed_per_game'], unique=False)
        batch_op.create_index('idx_org_save_percentage1', ['org_id', 'save_percentage'], unique=False)
        batch_op.create_index('idx_org_shots_faced1', ['org_id', 'shots_faced'], unique=False)

    op.create_table('org_stats_human',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('human_id', sa.Integer(), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('games_total', sa.Integer(), nullable=True),
    sa.Column('games_skater', sa.Integer(), nullable=True),
    sa.Column('games_referee', sa.Integer(), nullable=True),
    sa.Column('games_scorekeeper', sa.Integer(), nullable=True),
    sa.Column('games_goalie', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['human_id'], ['humans.id'], ),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('human_id', 'org_id', name='_human_org_stats_uc1')
    )
    with op.batch_alter_table('org_stats_human', schema=None) as batch_op:
        batch_op.create_index('idx_org_games_goalie1', ['org_id', 'games_goalie'], unique=False)
        batch_op.create_index('idx_org_games_referee1', ['org_id', 'games_referee'], unique=False)
        batch_op.create_index('idx_org_games_scorekeeper1', ['org_id', 'games_scorekeeper'], unique=False)
        batch_op.create_index('idx_org_games_skater1', ['org_id', 'games_skater'], unique=False)
        batch_op.create_index('idx_org_games_total1', ['org_id', 'games_total'], unique=False)

    op.create_table('org_stats_skater',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('human_id', sa.Integer(), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('games_played', sa.Integer(), nullable=True),
    sa.Column('goals', sa.Integer(), nullable=True),
    sa.Column('assists', sa.Integer(), nullable=True),
    sa.Column('points', sa.Integer(), nullable=True),
    sa.Column('penalties', sa.Integer(), nullable=True),
    sa.Column('goals_per_game', sa.Float(), nullable=True),
    sa.Column('points_per_game', sa.Float(), nullable=True),
    sa.Column('assists_per_game', sa.Float(), nullable=True),
    sa.Column('penalties_per_game', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['human_id'], ['humans.id'], ),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('human_id', 'org_id', name='_human_org_uc_skater1')
    )
    with op.batch_alter_table('org_stats_skater', schema=None) as batch_op:
        batch_op.create_index('idx_org_assists_per_game3', ['org_id', 'assists_per_game'], unique=False)
        batch_op.create_index('idx_org_games_played3', ['org_id', 'games_played'], unique=False)
        batch_op.create_index('idx_org_goals_per_game3', ['org_id', 'goals_per_game'], unique=False)
        batch_op.create_index('idx_org_penalties_per_game3', ['org_id', 'penalties_per_game'], unique=False)
        batch_op.create_index('idx_org_points_per_game3', ['org_id', 'points_per_game'], unique=False)

    with op.batch_alter_table('goalie_org_stats', schema=None) as batch_op:
        batch_op.drop_index('idx_org_games_played_goalie')
        batch_op.drop_index('idx_org_goals_allowed')
        batch_op.drop_index('idx_org_goals_allowed_per_game')
        batch_op.drop_index('idx_org_save_percentage')
        batch_op.drop_index('idx_org_shots_faced')

    op.drop_table('goalie_org_stats')
    with op.batch_alter_table('skater_org_stats', schema=None) as batch_op:
        batch_op.drop_index('idx_org_assists_per_game2')
        batch_op.drop_index('idx_org_games_played2')
        batch_op.drop_index('idx_org_goals_per_game2')
        batch_op.drop_index('idx_org_penalties_per_game2')
        batch_op.drop_index('idx_org_points_per_game2')

    op.drop_table('skater_org_stats')
    with op.batch_alter_table('human_org_stats', schema=None) as batch_op:
        batch_op.drop_index('idx_org_games_goalie')
        batch_op.drop_index('idx_org_games_referee')
        batch_op.drop_index('idx_org_games_scorekeeper')
        batch_op.drop_index('idx_org_games_skater')
        batch_op.drop_index('idx_org_games_total')

    op.drop_table('human_org_stats')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('human_org_stats',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('human_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('org_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('games_total', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('games_skater', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('games_referee', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('games_scorekeeper', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('games_goalie', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['human_id'], ['humans.id'], name='human_org_stats_human_id_fkey'),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], name='human_org_stats_org_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='human_org_stats_pkey'),
    sa.UniqueConstraint('human_id', 'org_id', name='_human_org_stats_uc')
    )
    with op.batch_alter_table('human_org_stats', schema=None) as batch_op:
        batch_op.create_index('idx_org_games_total', ['org_id', 'games_total'], unique=False)
        batch_op.create_index('idx_org_games_skater', ['org_id', 'games_skater'], unique=False)
        batch_op.create_index('idx_org_games_scorekeeper', ['org_id', 'games_scorekeeper'], unique=False)
        batch_op.create_index('idx_org_games_referee', ['org_id', 'games_referee'], unique=False)
        batch_op.create_index('idx_org_games_goalie', ['org_id', 'games_goalie'], unique=False)

    op.create_table('skater_org_stats',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('human_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('org_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('games_played', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('goals', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('assists', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('points', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('penalties', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('goals_per_game', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('points_per_game', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('assists_per_game', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('penalties_per_game', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['human_id'], ['humans.id'], name='skater_org_stats_human_id_fkey'),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], name='skater_org_stats_org_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='skater_org_stats_pkey'),
    sa.UniqueConstraint('human_id', 'org_id', name='_human_org_uc_skater')
    )
    with op.batch_alter_table('skater_org_stats', schema=None) as batch_op:
        batch_op.create_index('idx_org_points_per_game2', ['org_id', 'points_per_game'], unique=False)
        batch_op.create_index('idx_org_penalties_per_game2', ['org_id', 'penalties_per_game'], unique=False)
        batch_op.create_index('idx_org_goals_per_game2', ['org_id', 'goals_per_game'], unique=False)
        batch_op.create_index('idx_org_games_played2', ['org_id', 'games_played'], unique=False)
        batch_op.create_index('idx_org_assists_per_game2', ['org_id', 'assists_per_game'], unique=False)

    op.create_table('goalie_org_stats',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('human_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('org_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('games_played', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('goals_allowed', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('goals_allowed_per_game', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('shots_faced', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('save_percentage', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['human_id'], ['humans.id'], name='goalie_org_stats_human_id_fkey'),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], name='goalie_org_stats_org_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='goalie_org_stats_pkey'),
    sa.UniqueConstraint('human_id', 'org_id', name='_human_org_uc_goalie')
    )
    with op.batch_alter_table('goalie_org_stats', schema=None) as batch_op:
        batch_op.create_index('idx_org_shots_faced', ['org_id', 'shots_faced'], unique=False)
        batch_op.create_index('idx_org_save_percentage', ['org_id', 'save_percentage'], unique=False)
        batch_op.create_index('idx_org_goals_allowed_per_game', ['org_id', 'goals_allowed_per_game'], unique=False)
        batch_op.create_index('idx_org_goals_allowed', ['org_id', 'goals_allowed'], unique=False)
        batch_op.create_index('idx_org_games_played_goalie', ['org_id', 'games_played'], unique=False)

    with op.batch_alter_table('org_stats_skater', schema=None) as batch_op:
        batch_op.drop_index('idx_org_points_per_game3')
        batch_op.drop_index('idx_org_penalties_per_game3')
        batch_op.drop_index('idx_org_goals_per_game3')
        batch_op.drop_index('idx_org_games_played3')
        batch_op.drop_index('idx_org_assists_per_game3')

    op.drop_table('org_stats_skater')
    with op.batch_alter_table('org_stats_human', schema=None) as batch_op:
        batch_op.drop_index('idx_org_games_total1')
        batch_op.drop_index('idx_org_games_skater1')
        batch_op.drop_index('idx_org_games_scorekeeper1')
        batch_op.drop_index('idx_org_games_referee1')
        batch_op.drop_index('idx_org_games_goalie1')

    op.drop_table('org_stats_human')
    with op.batch_alter_table('org_stats_goalie', schema=None) as batch_op:
        batch_op.drop_index('idx_org_shots_faced1')
        batch_op.drop_index('idx_org_save_percentage1')
        batch_op.drop_index('idx_org_goals_allowed_per_game1')
        batch_op.drop_index('idx_org_goals_allowed1')
        batch_op.drop_index('idx_org_games_played_goalie1')

    op.drop_table('org_stats_goalie')
    # ### end Alembic commands ###
