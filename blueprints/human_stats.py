import sys, os
from flask import Blueprint, request, jsonify, render_template, url_for

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from hockey_blast_common_lib.models import db, Organization, Team, GameRoster, Game, Division, Human, Goal, Penalty, Level
from hockey_blast_common_lib.stats_models import OrgStatsHuman, OrgStatsSkater, OrgStatsGoalie, OrgStatsReferee
from hockey_blast_common_lib.stats_utils import ALL_ORGS_ID
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio
from sqlalchemy import func, cast, Integer

human_stats_bp = Blueprint('human_stats', __name__)

@human_stats_bp.route('/human_stats', methods=['GET'])
def human_stats():
    human_id = request.args.get('human_id')
    top_n = request.args.get('top_n', default=20, type=int)
    org_id = ALL_ORGS_ID
    if not human_id:
        return jsonify({"error": "Please provide human_id"}), 400
    
    human_id = int(human_id)  # Ensure human_id is an integer
    
    # Fetch the human's name from the Human table
    human = db.session.query(Human).filter(Human.id == human_id).first()
    if not human:
        return jsonify({"error": "Human not found"}), 404
    
    full_name = f"{human.first_name} {human.middle_name} {human.last_name}".strip()
    
    roles_data = []

    def calculate_rank(rank, total, reverse=False):
        percentile = (rank / total) * 100
        if reverse:
            percentile = 100 - percentile
        return f"{rank}/{total} ({round(percentile)}pct)"

    # Fetch overall stats from OrgStatsHuman for all organizations
    org_stats = db.session.query(OrgStatsHuman).filter(OrgStatsHuman.human_id == human_id, OrgStatsHuman.org_id == org_id).first()

    if org_stats:
        if org_stats.games_skater > 0:
            skater_first_game = db.session.query(Game.date, Game.time).filter(Game.id == org_stats.first_game_id_skater).first()
            skater_last_game = db.session.query(Game.date, Game.time).filter(Game.id == org_stats.last_game_id_skater).first()
            skater_first_game_link = f"<a href='{url_for('game_card.game_card', game_id=org_stats.first_game_id_skater)}'>{skater_first_game.date.strftime('%m/%d/%y')}</a>" if skater_first_game else None
            skater_last_game_link = f"<a href='{url_for('game_card.game_card', game_id=org_stats.last_game_id_skater)}'>{skater_last_game.date.strftime('%m/%d/%y')}</a>" if skater_last_game else None
            roles_data.append({
                'role': f"Skater <a href='{url_for('skater_performance.skater_performance', human_id=human_id)}'>(Click here for all stats)</a>",
                'games_count': org_stats.games_skater,
                'rank': calculate_rank(org_stats.games_skater_rank, org_stats.skaters_in_rank),
                'first_date': skater_first_game_link,
                'last_date': skater_last_game_link
            })
        if org_stats.games_goalie > 0:
            goalie_first_game = db.session.query(Game.date, Game.time).filter(Game.id == org_stats.first_game_id_goalie).first()
            goalie_last_game = db.session.query(Game.date, Game.time).filter(Game.id == org_stats.last_game_id_goalie).first()
            goalie_first_game_link = f"<a href='{url_for('game_card.game_card', game_id=org_stats.first_game_id_goalie)}'>{goalie_first_game.date.strftime('%m/%d/%y')}</a>" if goalie_first_game else None
            goalie_last_game_link = f"<a href='{url_for('game_card.game_card', game_id=org_stats.last_game_id_goalie)}'>{goalie_last_game.date.strftime('%m/%d/%y')}</a>" if goalie_last_game else None
            roles_data.append({
                'role': 'Goalie',
                'games_count': org_stats.games_goalie,
                'rank': calculate_rank(org_stats.games_goalie_rank, org_stats.goalies_in_rank),
                'first_date': goalie_first_game_link,
                'last_date': goalie_last_game_link
            })
        if org_stats.games_scorekeeper > 0:
            scorekeeper_first_game = db.session.query(Game.date, Game.time).filter(Game.id == org_stats.first_game_id_scorekeeper).first()
            scorekeeper_last_game = db.session.query(Game.date, Game.time).filter(Game.id == org_stats.last_game_id_scorekeeper).first()
            scorekeeper_first_game_link = f"<a href='{url_for('game_card.game_card', game_id=org_stats.first_game_id_scorekeeper)}'>{scorekeeper_first_game.date.strftime('%m/%d/%y')}</a>" if scorekeeper_first_game else None
            scorekeeper_last_game_link = f"<a href='{url_for('game_card.game_card', game_id=org_stats.last_game_id_scorekeeper)}'>{scorekeeper_last_game.date.strftime('%m/%d/%y')}</a>" if scorekeeper_last_game else None
            roles_data.append({
                'role': 'Scorekeeper',
                'games_count': org_stats.games_scorekeeper,
                'rank': calculate_rank(org_stats.games_scorekeeper_rank, org_stats.scorekeepers_in_rank),
                'first_date': scorekeeper_first_game_link,
                'last_date': scorekeeper_last_game_link
            })
        if org_stats.games_referee > 0:
            referee_first_game = db.session.query(Game.date, Game.time).filter(Game.id == org_stats.first_game_id_referee).first()
            referee_last_game = db.session.query(Game.date, Game.time).filter(Game.id == org_stats.last_game_id_referee).first()
            referee_first_game_link = f"<a href='{url_for('game_card.game_card', game_id=org_stats.first_game_id_referee)}'>{referee_first_game.date.strftime('%m/%d/%y')}</a>" if referee_first_game else None
            referee_last_game_link = f"<a href='{url_for('game_card.game_card', game_id=org_stats.last_game_id_referee)}'>{referee_last_game.date.strftime('%m/%d/%y')}</a>" if referee_last_game else None
            roles_data.append({
                'role': 'Referee',
                'games_count': org_stats.games_referee,
                'rank': calculate_rank(org_stats.games_referee_rank, org_stats.referees_in_rank),
                'first_date': referee_first_game_link,
                'last_date': referee_last_game_link
            })

    # Query for Referee role
    org_referee_stats = db.session.query(OrgStatsReferee).filter(OrgStatsReferee.human_id == human_id, OrgStatsReferee.org_id == org_id).first()
    referee_performance = {}
    if org_referee_stats and org_referee_stats.games_reffed > 0:
        referee_games_count = org_referee_stats.games_reffed
        referee_first_game_id = org_referee_stats.first_game_id
        referee_first_game = db.session.query(Game.date, Game.time).filter(Game.id == referee_first_game_id).first()
        referee_first_game_date = pd.Timestamp(f"{referee_first_game.date} {referee_first_game.time}")
        referee_last_game_id = org_referee_stats.last_game_id
        referee_last_game = db.session.query(Game.date, Game.time).filter(Game.id == referee_last_game_id).first()
        referee_last_game_date = pd.Timestamp(f"{referee_last_game.date} {referee_last_game.time}")
        referee_first_game_link = f"<a href='{url_for('game_card.game_card', game_id=referee_first_game_id)}'>{referee_first_game_date.strftime('%m/%d/%y %I:%M%p')}</a>" if referee_first_game_id else None
        referee_last_game_link = f"<a href='{url_for('game_card.game_card', game_id=referee_last_game_id)}'>{referee_last_game_date.strftime('%m/%d/%y %I:%M%p')}</a>" if referee_last_game_id else None
        referee_performance.update({
            'penalties_given': f"{org_referee_stats.penalties_given} ({calculate_rank(org_referee_stats.penalties_given_rank, org_referee_stats.total_in_rank)})",
            'penalties_per_game': f"{org_referee_stats.penalties_per_game:.2f} ({calculate_rank(org_referee_stats.penalties_per_game_rank, org_referee_stats.total_in_rank)})",
            'gm_given': f"{org_referee_stats.gm_given} ({calculate_rank(org_referee_stats.gm_given_rank, org_referee_stats.total_in_rank)})",
            'gm_per_game': f"{org_referee_stats.gm_per_game:.2f} ({calculate_rank(org_referee_stats.gm_per_game_rank, org_referee_stats.total_in_rank)})"
        })
    else:
        referee_first_game_id = None
        referee_last_game_id = None
        referee_first_game_date = None
        referee_last_game_date = None
        referee_first_game_link = None
        referee_last_game_link = None


    # Query for Goalie role
    org_goalie_stats = db.session.query(OrgStatsGoalie).filter(OrgStatsGoalie.human_id == human_id, OrgStatsGoalie.org_id == org_id).first()
    goalie_performance = {}
    if org_goalie_stats and org_goalie_stats.games_played > 0:
        goalie_games_count = org_goalie_stats.games_played
        goalie_first_game_id = org_goalie_stats.first_game_id
        goalie_first_game = db.session.query(Game.date, Game.time).filter(Game.id == goalie_first_game_id).first()
        goalie_first_game_date = pd.Timestamp(f"{goalie_first_game.date} {goalie_first_game.time}")
        goalie_last_game_id = org_goalie_stats.last_game_id
        goalie_last_game = db.session.query(Game.date, Game.time).filter(Game.id == goalie_last_game_id).first()
        goalie_last_game_date = pd.Timestamp(f"{goalie_last_game.date} {goalie_last_game.time}")
        goalie_first_game_link = f"<a href='{url_for('game_card.game_card', game_id=goalie_first_game_id)}'>{goalie_first_game_date.strftime('%m/%d/%y %I:%M%p')}</a>" if goalie_first_game_id else None
        goalie_last_game_link = f"<a href='{url_for('game_card.game_card', game_id=goalie_last_game_id)}'>{goalie_last_game_date.strftime('%m/%d/%y %I:%M%p')}</a>" if goalie_last_game_id else None
        

        goalie_performance.update({
            'games': f"{org_goalie_stats.games_played} ({calculate_rank(org_goalie_stats.games_played_rank, org_goalie_stats.total_in_rank)})",
            'goals_allowed': org_goalie_stats.goals_allowed,
            'goals_allowed_per_game': f"{org_goalie_stats.goals_allowed_per_game:.2f} ({calculate_rank(org_goalie_stats.goals_allowed_per_game_rank, org_goalie_stats.total_in_rank, reverse=True)})",
            'shots_faced': f"{org_goalie_stats.shots_faced} ({calculate_rank(org_goalie_stats.shots_faced_rank, org_goalie_stats.total_in_rank)})",
            'save_percentage': f"{org_goalie_stats.save_percentage:.2f} ({calculate_rank(org_goalie_stats.save_percentage_rank, org_goalie_stats.total_in_rank)})"
        })
    else:
        goalie_games_count = 0
        goalie_first_game_id = None
        goalie_last_game_id = None
        goalie_first_game_date = None
        goalie_last_game_date = None
        goalie_first_game_link = None
        goalie_last_game_link = None



    # Fetch skater stats from OrgStatsSkater
    org_skater_stats = db.session.query(OrgStatsSkater).filter(OrgStatsSkater.human_id == human_id, OrgStatsSkater.org_id == org_id).first()

    skater_performance = {}
    if org_skater_stats and org_skater_stats.games_played > 0:
        skater_performance.update({
            'goals': org_skater_stats.goals,
            'assists': org_skater_stats.assists,
            'points': org_skater_stats.points,
            'goals_per_game': f"{org_skater_stats.goals_per_game:.2f} ({calculate_rank(org_skater_stats.goals_per_game_rank, org_skater_stats.total_in_rank)})",
            'assists_per_game': f"{org_skater_stats.assists_per_game:.2f} ({calculate_rank(org_skater_stats.assists_per_game_rank, org_skater_stats.total_in_rank)})",
            'points_per_game': f"{org_skater_stats.points_per_game:.2f} ({calculate_rank(org_skater_stats.points_per_game_rank, org_skater_stats.total_in_rank)})",
            'penalties': org_skater_stats.penalties,
            'penalties_per_game': f"{org_skater_stats.penalties_per_game:.2f} ({calculate_rank(org_skater_stats.penalties_per_game_rank, org_skater_stats.total_in_rank)})"
        })

        skater_first_game_id = org_skater_stats.first_game_id
        skater_first_game = db.session.query(Game.date, Game.time).filter(Game.id == skater_first_game_id).first()
        skater_first_game_date = pd.Timestamp(f"{skater_first_game.date} {skater_first_game.time}")
        skater_last_game_id = org_skater_stats.last_game_id
        skater_last_game = db.session.query(Game.date, Game.time).filter(Game.id == skater_last_game_id).first()
        skater_last_game_date = pd.Timestamp(f"{skater_last_game.date} {skater_last_game.time}")
        skater_first_game_link = f"<a href='{url_for('game_card.game_card', game_id=skater_first_game_id)}'>{skater_first_game_date.strftime('%m/%d/%y %I:%M%p')}</a>" if skater_first_game_id else None
        skater_last_game_link = f"<a href='{url_for('game_card.game_card', game_id=skater_last_game_id)}'>{skater_last_game_date.strftime('%m/%d/%y %I:%M%p')}</a>" if skater_last_game_id else None
    else:
        skater_first_game_id = None
        skater_last_game_id = None
        skater_first_game_date = None
        skater_last_game_date = None
        skater_first_game_link = None
        skater_last_game_link = None

    # Pull all rosters where this human was present
    rosters = db.session.query(GameRoster, Game, Division).join(Game, GameRoster.game_id == Game.id).join(Division, Game.division_id == Division.id).filter(GameRoster.human_id == human_id).all() #, Division.org_id == org_id).all()
    
    # Convert rosters to a dataframe
    rosters_df = pd.DataFrame([(r.GameRoster.team_id,
                                r.GameRoster.game_id,
                                r.Game.division_id,
                                r.Division.level_id,
                                r.Game.date,
                                r.Game.time,
                                r.GameRoster.role,
                                r.GameRoster.jersey_number,
                                r.Game.home_final_score if r.GameRoster.team_id == r.Game.home_team_id else r.Game.visitor_final_score,
                                (r.Game.home_period_1_shots or 0) + (r.Game.home_period_2_shots or 0) + (r.Game.home_period_3_shots or 0) + (r.Game.home_ot_shots or 0) + (r.Game.home_so_shots or 0) if r.GameRoster.team_id == r.Game.visitor_team_id else (r.Game.visitor_period_1_shots or 0) + (r.Game.visitor_period_2_shots or 0) + (r.Game.visitor_period_3_shots or 0) + (r.Game.visitor_ot_shots or 0) + (r.Game.visitor_so_shots or 0)) for r in rosters],
                                columns=['team_id',
                                         'game_id',
                                         'division_id',
                                         'level_id',
                                         'game_date',
                                         'game_time',
                                         'role',
                                         'jersey_number',
                                         'goals_allowed',
                                         'shots_faced'])

    # Filter out rows where both goals_allowed and shots_faced are zero

    # Convert game_date and game_time to datetime
    rosters_df['game_date'] = pd.to_datetime(rosters_df['game_date'])
    rosters_df['game_time'] = pd.to_datetime(rosters_df['game_time'], format='%H:%M:%S').dt.time
    rosters_df['game_datetime'] = pd.to_datetime(rosters_df['game_date'].astype(str) + ' ' + rosters_df['game_time'].astype(str))
    
    # Sort rosters_df by game_datetime in descending order
    rosters_df = rosters_df.sort_values(by='game_datetime', ascending=False)
    
    # Extract first and last game dates for Skater
    player_rosters_df = rosters_df[~((rosters_df['role'].str.upper() == 'G') | (rosters_df['jersey_number'].str.upper() == 'G'))]

    skater_first_game_date = player_rosters_df['game_date'].min() if not player_rosters_df.empty else None
    skater_last_game_date = player_rosters_df['game_date'].max() if not player_rosters_df.empty else None
    skater_first_game_id = player_rosters_df.loc[player_rosters_df['game_date'] == skater_first_game_date, 'game_id'].values[0] if skater_first_game_date else None
    skater_last_game_id = player_rosters_df.loc[player_rosters_df['game_date'] == skater_last_game_date, 'game_id'].values[0] if skater_last_game_date else None

    # Prepare links for skater first and last game dates
    skater_first_game_link = f"<a href='{url_for('game_card.game_card', game_id=skater_first_game_id)}'>{skater_first_game_date.strftime('%m/%d/%y')}</a>" if skater_first_game_date else None
    skater_last_game_link = f"<a href='{url_for('game_card.game_card', game_id=skater_last_game_id)}'>{skater_last_game_date.strftime('%m/%d/%y')}</a>" if skater_last_game_date else None

    # Extract first and last game dates for Goalie
    goalie_rosters_df = rosters_df[(rosters_df['role'].str.upper() == 'G') | (rosters_df['jersey_number'].str.upper() == 'G')]


    # Extract first and last game dates for Player
    first_game_date = rosters_df['game_date'].min() if not rosters_df.empty else None
    last_game_date = rosters_df['game_date'].max() if not rosters_df.empty else None
    first_game_id = rosters_df.loc[rosters_df['game_date'] == first_game_date, 'game_id'].values[0] if first_game_date else None
    last_game_id = rosters_df.loc[rosters_df['game_date'] == last_game_date, 'game_id'].values[0] if last_game_date else None


    # Filter out roles where role or jersey_number is "G" or "g"
    player_rosters_df = rosters_df[~((rosters_df['role'].str.upper() == 'G') | (rosters_df['jersey_number'].str.upper() == 'G'))]

    # Filter for Goalie role
    goalie_rosters_df = rosters_df[(rosters_df['role'].str.upper() == 'G') | (rosters_df['jersey_number'].str.upper() == 'G')]

    goalie_games_count = len(goalie_rosters_df['game_id'].unique())
   
    # Query for Scorekeeper role
    scorekeeper_games = db.session.query(Game).filter(
        (Game.scorekeeper_id == human_id)
    ).all()
    scorekeeper_game_dates = [game.date for game in scorekeeper_games]
    scorekeeper_game_dates = pd.to_datetime(scorekeeper_game_dates)
    scorekeeper_first_game_date = min(scorekeeper_game_dates) if not scorekeeper_game_dates.empty else None
    scorekeeper_last_game_date = max(scorekeeper_game_dates) if not scorekeeper_game_dates.empty else None
    scorekeeper_first_game_id = scorekeeper_games[scorekeeper_game_dates.argmin()].id if scorekeeper_first_game_date else None
    scorekeeper_last_game_id = scorekeeper_games[scorekeeper_game_dates.argmax()].id if scorekeeper_last_game_date else None

    # Prepare links for first and last game dates
    scorekeeper_first_game_link = f"<a href='{url_for('game_card.game_card', game_id=scorekeeper_first_game_id)}'>{scorekeeper_first_game_date.strftime('%m/%d/%y')}</a>" if scorekeeper_first_game_date else None
    scorekeeper_last_game_link = f"<a href='{url_for('game_card.game_card', game_id=scorekeeper_last_game_id)}'>{scorekeeper_last_game_date.strftime('%m/%d/%y')}</a>" if scorekeeper_last_game_date else None
    
    # Query for Referee role
    referee_games = db.session.query(Game).filter(
        (Game.referee_1_id == human_id) | (Game.referee_2_id == human_id)
    ).all()
    referee_game_dates = [game.date for game in referee_games]
    referee_game_dates = pd.to_datetime(referee_game_dates)  
    
    # Find the earliest and latest dates across all roles
    all_dates = [pd.Timestamp(date) for date in [first_game_date, goalie_first_game_date, scorekeeper_first_game_date, referee_first_game_date] if date] + \
                [pd.Timestamp(date) for date in [last_game_date, goalie_last_game_date, scorekeeper_last_game_date, referee_last_game_date] if date]
    overall_first_game_date = min(all_dates) if all_dates else None
    overall_last_game_date = max(all_dates) if all_dates else None

    # Get the corresponding game IDs for overall first and last game dates
    overall_first_game_id = None
    overall_last_game_id = None

    if overall_first_game_date:
        if overall_first_game_date == pd.Timestamp(first_game_date):
            overall_first_game_id = first_game_id
        elif overall_first_game_date == pd.Timestamp(goalie_first_game_date):
            overall_first_game_id = goalie_first_game_id
        elif overall_first_game_date == pd.Timestamp(scorekeeper_first_game_date):
            overall_first_game_id = scorekeeper_first_game_id
        elif overall_first_game_date == pd.Timestamp(referee_first_game_date):
            overall_first_game_id = referee_first_game_id

    if overall_last_game_date:
        if overall_last_game_date == pd.Timestamp(last_game_date):
            overall_last_game_id = last_game_id
        elif overall_last_game_date == pd.Timestamp(goalie_last_game_date):
            overall_last_game_id = goalie_last_game_id
        elif overall_last_game_date == pd.Timestamp(scorekeeper_last_game_date):
            overall_last_game_id = scorekeeper_last_game_id
        elif overall_last_game_date == pd.Timestamp(referee_last_game_date):
            overall_last_game_id = referee_last_game_id

    # Prepare links for overall first and last game dates
    overall_first_game_link = f"<a href='{url_for('game_card.game_card', game_id=overall_first_game_id)}'>{overall_first_game_date.strftime('%m/%d/%y')}</a>" if overall_first_game_date else None
    overall_last_game_link = f"<a href='{url_for('game_card.game_card', game_id=overall_last_game_id)}'>{overall_last_game_date.strftime('%m/%d/%y')}</a>" if overall_last_game_date else None

    # Append dates to human name
    display_name = f"{full_name} ({overall_first_game_link} - {overall_last_game_link})"
    
    # Count how many games were played for each team
    team_game_counts = rosters_df.groupby('team_id').size().reset_index(name='games_played').sort_values(by='games_played', ascending=False)
    
    # Get top N teams
    top_teams = team_game_counts.head(top_n)
    
    # Get team names and prepare data for the template
    most_games_played = []
    for _, row in top_teams.iterrows():
        team_id = int(row['team_id'])  # Convert to standard Python integer
        team_name = db.session.query(Team.name).filter(Team.id == team_id).first()[0]
        most_games_played.append({
            'team_id': team_id,
            'team_name': team_name,
            'games_played': row['games_played']
        })
    
    # Convert level_id to integer
    rosters_df['level_id'] = rosters_df['level_id'].astype(int)

    # Count how many games were played for each level
    level_game_counts = rosters_df.groupby('level_id').size().reset_index(name='games_played').sort_values(by='games_played', ascending=False)
    
    # Get top N levels
    top_skater_levels = level_game_counts.head(top_n)
    
    # Count points (goals + assists) per level
    goals = db.session.query(Goal).filter((Goal.goal_scorer_id == human_id) | (Goal.assist_1_id == human_id) | (Goal.assist_2_id == human_id)).all()
    goals_df = pd.DataFrame([(g.game_id, g.goal_scorer_id, g.assist_1_id, g.assist_2_id) for g in goals], columns=['game_id', 'goal_scorer_id', 'assist_1_id', 'assist_2_id'])
    goals_df = goals_df.merge(rosters_df[['game_id', 'level_id']], on='game_id', how='left')
    points_per_level = goals_df.groupby('level_id').size().reset_index(name='points')
    
    # Merge points with level game counts
    level_stats = top_skater_levels.merge(points_per_level, on='level_id', how='left').fillna(0)
    level_stats['points_per_game'] = level_stats['points'] / level_stats['games_played']
    
    # Prepare data for the template
    skater_level_stats = []
    for _, row in level_stats.iterrows():
        level = db.session.query(Level).filter(Level.id == int(row['level_id'])).first()
        level_name = f"{level.level_name} ({level.level_alternative_name})" if level.level_alternative_name else level.level_name
        skater_level_stats.append({
            'level_name': level_name,
            'games_played': row['games_played'],
            'points_per_game': row['points_per_game']
        })

    goalie_level_stats = []
    # Calculate most_level_games_goaltended
    if goalie_games_count > 0:
        goalie_level_game_counts = goalie_rosters_df.groupby('level_id').size().reset_index(name='games_played').sort_values(by='games_played', ascending=False)
        for _, row in goalie_level_game_counts.iterrows():
            level = db.session.query(Level).filter(Level.id == int(row['level_id'])).first()
            level_name = f"{level.level_name} ({level.level_alternative_name})" if level.level_alternative_name else level.level_name
            games_played = row['games_played']
            goals_allowed = goalie_rosters_df[goalie_rosters_df['level_id'] == row['level_id']]['goals_allowed'].sum()
            shots_faced = goalie_rosters_df[goalie_rosters_df['level_id'] == row['level_id']]['shots_faced'].sum()
            save_percentage = ((shots_faced - goals_allowed) / shots_faced) * 100 if shots_faced > 0 else 0
            goals_allowed_per_game = goals_allowed / games_played if games_played > 0 else 0
            goalie_level_stats.append({
                'level_name': level_name,
                'games_played': games_played,
                'goals_allowed': goals_allowed,
                'goals_allowed_per_game': goals_allowed_per_game,
                'shots_faced': shots_faced,
                'save_percentage': save_percentage
            })
    
    # Pull all humans who played together with the given human_id
    excluded_names = ["Not Signed In", "No Credit- Roster", "No Goalie", "Goalie Not Noted"]
    teammate_rosters = db.session.query(GameRoster).join(Human).filter(
        GameRoster.game_id.in_(rosters_df['game_id']),
        GameRoster.human_id != human_id,
        ~((Human.first_name + ' ' + Human.middle_name + ' ' + Human.last_name).in_(excluded_names))
    ).all()
    
    # Convert teammate rosters to a dataframe
    teammate_rosters_df = pd.DataFrame([(r.human_id, r.game_id) for r in teammate_rosters], columns=['teammate_id', 'game_id'])
    
    # Count how many games were played with each teammate
    teammate_game_counts = teammate_rosters_df.groupby('teammate_id').size().reset_index(name='games_played').sort_values(by='games_played', ascending=False)
    
    # Get top N teammates
    top_teammates = teammate_game_counts.head(top_n)
    
    # Get teammate names and prepare data for the template
    teammates = []
    for _, row in top_teammates.iterrows():
        teammate_id = int(row['teammate_id'])  # Convert to standard Python integer
        teammate_name = db.session.query(Human).filter(Human.id == teammate_id).first()
        full_teammate_name = f"{teammate_name.first_name} {teammate_name.middle_name} {teammate_name.last_name}".strip()
        teammates.append({
            'teammate_id': teammate_id,
            'teammate_name': full_teammate_name,
            'games_played': row['games_played']
        })
    
    # Prepare data for Plotly plot
    player_games_per_month = player_rosters_df['game_date'].dt.to_period('M').value_counts().sort_index()
    goalie_games_per_month = goalie_rosters_df['game_date'].dt.to_period('M').value_counts().sort_index()
    scorekeeper_games_per_month = pd.Series(scorekeeper_game_dates).dt.to_period('M').value_counts().sort_index()
    referee_games_per_month = pd.Series(referee_game_dates).dt.to_period('M').value_counts().sort_index()
    
    # Determine the overall date range for the plot
    all_dates = pd.concat([player_games_per_month, goalie_games_per_month, scorekeeper_games_per_month, referee_games_per_month]).index
    if not all_dates.empty:
        all_months = pd.period_range(start=all_dates.min(), end=all_dates.max(), freq='M')
        player_games_per_month = player_games_per_month.reindex(all_months, fill_value=0)
        goalie_games_per_month = goalie_games_per_month.reindex(all_months, fill_value=0)
        scorekeeper_games_per_month = scorekeeper_games_per_month.reindex(all_months, fill_value=0)
        referee_games_per_month = referee_games_per_month.reindex(all_months, fill_value=0)
        
    plot_data = []
    if player_games_per_month.sum() > 0:
        plot_data.append(go.Scatter(x=player_games_per_month.index.astype(str), y=player_games_per_month.values, mode='lines', name='Skater', line=dict(color='#FF6347')))  # Tomato
    if goalie_games_per_month.sum() > 0:
        plot_data.append(go.Scatter(x=goalie_games_per_month.index.astype(str), y=goalie_games_per_month.values, mode='lines', name='Goalie', line=dict(color='#FFD700')))  # Gold
    if scorekeeper_games_per_month.sum() > 0:
        plot_data.append(go.Scatter(x=scorekeeper_games_per_month.index.astype(str), y=scorekeeper_games_per_month.values, mode='lines', name='Scorekeeper', line=dict(color='#32CD32')))  # Lime Green
    if referee_games_per_month.sum() > 0:
        plot_data.append(go.Scatter(x=referee_games_per_month.index.astype(str), y=referee_games_per_month.values, mode='lines', name='Referee', line=dict(color='#1E90FF')))  # Dodger Blue
    
    plot_layout = go.Layout(
        title='PulseLine',
        xaxis=dict(title='Month'),
        yaxis=dict(title='Number of Games'),
        plot_bgcolor='#20B2AA',  # Light teal
        paper_bgcolor='#008080',  # Dark teal
        font=dict(color='white')
    )
    plot_fig = go.Figure(data=plot_data, layout=plot_layout)
    plot_div = pio.to_html(plot_fig, full_html=False)
    
    # Extract recent games data
    recent_games_data = []
    day_of_week_map = {1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat', 7: 'Sun'}
    for _, row in rosters_df.head(top_n).iterrows():  # Limit to top_n recent games
        game = db.session.query(Game).filter(Game.id == row['game_id']).first()
        visitor_team = db.session.query(Team).filter(Team.id == game.visitor_team_id).first()
        home_team = db.session.query(Team).filter(Team.id == game.home_team_id).first()
        day_of_week = day_of_week_map.get(game.day_of_week, '')
        date_time = f"{day_of_week} {game.date.strftime('%m/%d/%y')} {game.time.strftime('%I:%M%p')}"
        if game.status.startswith('Final'):
            if game.home_team_id == row['team_id']:
                if game.home_final_score > game.visitor_final_score:
                    color = "#7CFC00"
                elif game.home_final_score < game.visitor_final_score:
                    color = "red"
                else:
                    color = "black"
                final_score = f"<span style='color:black;'>{game.visitor_final_score}</span> : <strong style='color:{color};'>{game.home_final_score}</strong>"
            elif game.visitor_team_id == row['team_id']:
                if game.visitor_final_score > game.home_final_score:
                    color = "#7CFC00"
                elif game.visitor_final_score < game.home_final_score:
                    color = "red"
                else:
                    color = "black"
                final_score = f"<strong style='color:{color};'>{game.visitor_final_score}</strong> : <span style='color:black;'>{game.home_final_score}</span>"
            else:
                final_score = f"<span style='color:black;'>{game.visitor_final_score}</span> : <span style='color:black;'>{game.home_final_score}</span>"
        else:
            # Handle cases where the game status is not 'Final'
            final_score = "N/A"
        
        # Calculate player stats
        goals_in_game = db.session.query(Goal).filter(Goal.game_id == game.id, Goal.goal_scorer_id == human_id).count()
        assists_in_game = db.session.query(Goal).filter(Goal.game_id == game.id, (Goal.assist_1_id == human_id) | (Goal.assist_2_id == human_id)).count()
        
        # Separate numeric and non-numeric penalty minutes
        penalties = db.session.query(Penalty.penalty_minutes).filter(Penalty.game_id == game.id, Penalty.penalized_player_id == human_id).all()
        numeric_penalty_minutes = 0
        non_numeric_penalties = []
        for penalty in penalties:
            try:
                numeric_penalty_minutes += int(penalty.penalty_minutes)
            except ValueError:
                non_numeric_penalties.append(penalty.penalty_minutes)
        
        player_stats = []
        if goals_in_game > 0:
            player_stats.append(f"{goals_in_game}G")
        if assists_in_game > 0:
            player_stats.append(f"{assists_in_game}A")
        if numeric_penalty_minutes > 0:
            player_stats.append(f"{numeric_penalty_minutes}PIM")
        player_stats.extend(non_numeric_penalties)
        player_stats_str = " ".join(player_stats)
        
        # Make the team for which the human played bold
        if game.home_team_id == row['team_id']:
            team_names = f"<a href='{url_for('team_stats.team_stats', team_id=visitor_team.id)}'>{visitor_team.name}</a> at <strong><a href='{url_for('team_stats.team_stats', team_id=home_team.id)}'>{home_team.name}</a></strong>"
        else:
            team_names = f"<strong><a href='{url_for('team_stats.team_stats', team_id=visitor_team.id)}'>{visitor_team.name}</a></strong> at <a href='{url_for('team_stats.team_stats', team_id=home_team.id)}'>{home_team.name}</a>"

        recent_games_data.append({
            'date_time': f"<a href='{url_for('game_card.game_card', game_id=game.id)}'>{date_time}</a>",
            'team_names': team_names,
            'final_score': f"<a href='{url_for('game_card.game_card', game_id=game.id)}'>{final_score}</a>",
            'player_stats': player_stats_str
        })
    
    return render_template(
        'human_stats.html',
        display_name=display_name,
        roles_data=roles_data if len(roles_data) > 0 else [],
        most_games_played=most_games_played,
        skater_division_stats=skater_level_stats,
        goalie_division_stats=goalie_level_stats,
        teammates=teammates,
        skater_performance=skater_performance,
        goalie_performance=goalie_performance,
        referee_performance=referee_performance,
        plot_div=plot_div,
        recent_games_data=recent_games_data  # Pass recent games data to the template
    )