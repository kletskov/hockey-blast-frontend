import sys, os
from flask import Blueprint, request, jsonify, render_template, url_for

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from hockey_blast_common_lib.models import db, Organization, Team, GameRoster, Game, Division, Human, Goal, Penalty, Level
from hockey_blast_common_lib.stats_models import OrgStatsHuman
from hockey_blast_common_lib.h2h_models import SkaterToSkaterStats
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
        # Standard percentile: if you're better than X% of people, you're in Xth percentile
        # reverse=True means higher values are worse (like penalties)
        if reverse:
            percentile = (rank / total) * 100  # For penalties: higher rank = higher percentile (worse)
        else:
            percentile = (total - rank) / total * 100  # For good stats: lower rank = higher percentile (better)
        return f"{rank}/{total} ({round(percentile)}th)"

    # Fetch overall stats from OrgStatsHuman for all organizations
    org_stats = db.session.query(OrgStatsHuman).filter(OrgStatsHuman.human_id == human_id, OrgStatsHuman.org_id == org_id).first()

    # Batch load all game dates to avoid N+1 queries
    game_ids_to_fetch = []
    if org_stats:
        if org_stats.first_game_id_skater: game_ids_to_fetch.append(org_stats.first_game_id_skater)
        if org_stats.last_game_id_skater: game_ids_to_fetch.append(org_stats.last_game_id_skater)
        if org_stats.first_game_id_goalie: game_ids_to_fetch.append(org_stats.first_game_id_goalie)
        if org_stats.last_game_id_goalie: game_ids_to_fetch.append(org_stats.last_game_id_goalie)
        if org_stats.first_game_id_scorekeeper: game_ids_to_fetch.append(org_stats.first_game_id_scorekeeper)
        if org_stats.last_game_id_scorekeeper: game_ids_to_fetch.append(org_stats.last_game_id_scorekeeper)
        if org_stats.first_game_id_referee: game_ids_to_fetch.append(org_stats.first_game_id_referee)
        if org_stats.last_game_id_referee: game_ids_to_fetch.append(org_stats.last_game_id_referee)
        if org_stats.first_game_id: game_ids_to_fetch.append(org_stats.first_game_id)
        if org_stats.last_game_id: game_ids_to_fetch.append(org_stats.last_game_id)
    
    # Single query to get all needed game dates
    games_cache = {}
    if game_ids_to_fetch:
        games_data = db.session.query(Game.id, Game.date, Game.time).filter(Game.id.in_(game_ids_to_fetch)).all()
        games_cache = {game.id: game for game in games_data}

    if org_stats:
        if org_stats.games_skater > 0:
            skater_first_game = games_cache.get(org_stats.first_game_id_skater)
            skater_last_game = games_cache.get(org_stats.last_game_id_skater)
            skater_first_game_link = f"<a href='{url_for('game_card.game_card', game_id=org_stats.first_game_id_skater)}'>{skater_first_game.date.strftime('%m/%d/%y')}</a>" if skater_first_game else None
            skater_last_game_link = f"<a href='{url_for('game_card.game_card', game_id=org_stats.last_game_id_skater)}'>{skater_last_game.date.strftime('%m/%d/%y')}</a>" if skater_last_game else None
            roles_data.append({
                'role': f"Skater <a href='{url_for('skater_performance.skater_performance', human_id=human_id)}'>(See skater performance)</a>",
                'games_count': org_stats.games_skater,
                'rank': calculate_rank(org_stats.games_skater_rank, org_stats.skaters_in_rank),
                'first_date': skater_first_game_link,
                'last_date': skater_last_game_link
            })
        if org_stats.games_goalie > 0:
            goalie_first_game = games_cache.get(org_stats.first_game_id_goalie)
            goalie_last_game = games_cache.get(org_stats.last_game_id_goalie)
            goalie_first_game_link = f"<a href='{url_for('game_card.game_card', game_id=org_stats.first_game_id_goalie)}'>{goalie_first_game.date.strftime('%m/%d/%y')}</a>" if goalie_first_game else None
            goalie_last_game_link = f"<a href='{url_for('game_card.game_card', game_id=org_stats.last_game_id_goalie)}'>{goalie_last_game.date.strftime('%m/%d/%y')}</a>" if goalie_last_game else None
            roles_data.append({
                'role': f"Goalie <a href='{url_for('goalie_performance.goalie_performance', human_id=human_id)}'>(See goalie performance)</a>",
                'games_count': org_stats.games_goalie,
                'rank': calculate_rank(org_stats.games_goalie_rank, org_stats.goalies_in_rank),
                'first_date': goalie_first_game_link,
                'last_date': goalie_last_game_link
            })
        if org_stats.games_scorekeeper > 0:
            scorekeeper_first_game = games_cache.get(org_stats.first_game_id_scorekeeper)
            scorekeeper_last_game = games_cache.get(org_stats.last_game_id_scorekeeper)
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
            referee_first_game = games_cache.get(org_stats.first_game_id_referee)
            referee_last_game = games_cache.get(org_stats.last_game_id_referee)
            referee_first_game_link = f"<a href='{url_for('game_card.game_card', game_id=org_stats.first_game_id_referee)}'>{referee_first_game.date.strftime('%m/%d/%y')}</a>" if referee_first_game else None
            referee_last_game_link = f"<a href='{url_for('game_card.game_card', game_id=org_stats.last_game_id_referee)}'>{referee_last_game.date.strftime('%m/%d/%y')}</a>" if referee_last_game else None
            roles_data.append({
                'role': 'Referee',
                'games_count': org_stats.games_referee,
                'rank': calculate_rank(org_stats.games_referee_rank, org_stats.referees_in_rank),
                'first_date': referee_first_game_link,
                'last_date': referee_last_game_link
            })
    # Pull recent rosters where this human was present (limit to improve performance)
    rosters = db.session.query(GameRoster, Game, Division).join(Game, GameRoster.game_id == Game.id).join(Division, Game.division_id == Division.id).filter(GameRoster.human_id == human_id).order_by(Game.date.desc(), Game.time.desc()).limit(1000).all()
    
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
    
    overall_first_game_date = None
    overall_last_game_date = None

    overall_first_game_id = org_stats.first_game_id if org_stats else None
    overall_last_game_id = org_stats.last_game_id if org_stats else None
    overall_first_game_date = None
    overall_last_game_date = None
    if overall_first_game_id:
        overall_first_game = games_cache.get(overall_first_game_id)
        overall_first_game_date = overall_first_game.date if overall_first_game else None
    if overall_last_game_id:
        overall_last_game = games_cache.get(overall_last_game_id)
        overall_last_game_date = overall_last_game.date if overall_last_game else None

    # Prepare links for overall first and last game dates
    overall_first_game_link = f"<a href='{url_for('game_card.game_card', game_id=overall_first_game_id)}'>{overall_first_game_date.strftime('%m/%d/%y')}</a>" if overall_first_game_date else None
    overall_last_game_link = f"<a href='{url_for('game_card.game_card', game_id=overall_last_game_id)}'>{overall_last_game_date.strftime('%m/%d/%y')}</a>" if overall_last_game_date else None

    # Append dates to human name
    display_name = f"{full_name} ({overall_first_game_link} - {overall_last_game_link})"
    
    # Count how many games were played for each team
    team_game_counts = rosters_df.groupby('team_id').size().reset_index(name='games_played').sort_values(by='games_played', ascending=False)
    
    # Get top N teams
    top_teams = team_game_counts.head(top_n)
    
    # Batch load team names to avoid N+1 queries
    team_ids = top_teams['team_id'].tolist()
    teams_data = db.session.query(Team.id, Team.name).filter(Team.id.in_(team_ids)).all()
    teams_cache = {team.id: team.name for team in teams_data}
    
    # Get team names and prepare data for the template
    most_games_played = []
    for _, row in top_teams.iterrows():
        team_id = int(row['team_id'])  # Convert to standard Python integer
        team_name = teams_cache.get(team_id, 'Unknown Team')
        most_games_played.append({
            'team_id': team_id,
            'team_name': team_name,
            'games_played': row['games_played']
        })
    
    # Handle None values in level_id before converting to integer
    rosters_df['level_id'] = rosters_df['level_id'].fillna(0).astype(int)

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
    
    # Batch load teammate names to avoid N+1 queries
    teammate_ids = top_teammates['teammate_id'].tolist()
    teammates_data = db.session.query(Human.id, Human.first_name, Human.middle_name, Human.last_name).filter(Human.id.in_(teammate_ids)).all()
    teammates_cache = {human.id: f"{human.first_name} {human.middle_name} {human.last_name}".strip() for human in teammates_data}
    
    # Get teammate names and prepare data for the template
    teammates = []
    for _, row in top_teammates.iterrows():
        teammate_id = int(row['teammate_id'])  # Convert to standard Python integer
        full_teammate_name = teammates_cache.get(teammate_id, 'Unknown Player')
        teammates.append({
            'teammate_id': teammate_id,
            'teammate_name': full_teammate_name,
            'games_played': row['games_played']
        })
    
    # Get skater-to-skater stats if this person is a skater
    games_against_skaters = []
    has_skater_role = any(role['role'] for role in roles_data if 'Skater' in role['role'])
    
    if has_skater_role:
        # Query SkaterToSkaterStats where this human is either skater1 or skater2
        skater_stats = db.session.query(SkaterToSkaterStats).filter(
            (SkaterToSkaterStats.skater1_id == human_id) | 
            (SkaterToSkaterStats.skater2_id == human_id)
        ).order_by(SkaterToSkaterStats.games_against.desc()).limit(top_n).all()
        
        for stat in skater_stats:
            # Determine which is the opponent
            if stat.skater1_id == human_id:
                opponent_id = stat.skater2_id
                wins = stat.skater1_wins_vs_skater2
                losses = stat.skater2_wins_vs_skater1
            else:
                opponent_id = stat.skater1_id
                wins = stat.skater2_wins_vs_skater1
                losses = stat.skater1_wins_vs_skater2
            
            # Get opponent name
            opponent = db.session.query(Human).filter(Human.id == opponent_id).first()
            if opponent:
                opponent_name = f"{opponent.first_name} {opponent.middle_name} {opponent.last_name}".strip()
                
                # Format wins and losses with colors
                wins_formatted = f"<span style='color: #7CFC00;'>{wins}W</span>"
                losses_formatted = f"<span style='color: #FF0000;'>{losses}L</span>"
                
                games_against_skaters.append({
                    'opponent_id': opponent_id,
                    'opponent_name': opponent_name,
                    'games_against': stat.games_against,
                    'wins_losses': f"{wins_formatted} {losses_formatted}",
                    'skater_to_skater_link': f"/skater_to_skater/?human_id_1={human_id}&human_id_2={opponent_id}"
                })
    
        # Query for Referee role
    referee_games = db.session.query(Game).filter(
        (Game.referee_1_id == human_id) | (Game.referee_2_id == human_id)
    ).all()
    referee_game_dates = [game.date for game in referee_games]
    referee_game_dates = pd.to_datetime(referee_game_dates)  
    

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
    else:
        # Handle empty case - create empty period range
        all_months = pd.period_range(start=pd.Period('2020-01'), end=pd.Period('2020-01'), freq='M')

    # Dynamically adjust tick frequency based on the number of months
    num_months = len(all_months)
    if num_months > 200:  # Threshold for too many months
        tick_interval = 4  # Show every 3rd month
    elif num_months > 150:
        tick_interval = 3  # Show every 3rd month
    elif num_months > 50:
        tick_interval = 2
    else:
        tick_interval = 1  # Show every month

    tickvals = all_months[::tick_interval]  # Select ticks at the specified interval
    ticktext = tickvals.strftime('%b %Y')  # Format tick labels as "Month Year"

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
        title=dict(
            text='PulseLine',
            x=0.5  # Center the title
        ),
        xaxis=dict(
            title='Month',
            tickmode='array',  # Use array mode for ticks
            tickvals=tickvals.astype(str),  # Set tick values to the selected months
            ticktext=ticktext,  # Set tick labels
        ),
        yaxis=dict(title='Games per Month'),
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
        teammates=teammates,
        games_against_skaters=games_against_skaters,
        plot_div=plot_div,
        recent_games_data=recent_games_data  # Pass recent games data to the template
    )