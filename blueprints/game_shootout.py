import sys
from flask import Blueprint, request, render_template, jsonify, current_app
from hockey_blast_common_lib.models import db, Game, Division, Shootout, Season, League
import pandas as pd
from datetime import datetime
from sqlalchemy import and_

game_shootout_bp = Blueprint('game_shootout', __name__)

@game_shootout_bp.route('/game_shootout', methods=['GET'])
def interactive_plot():
    divisions = db.session.query(Division.level).filter(Division.org_id == 1).distinct().all()
    divisions = sorted([division[0] for division in divisions])  # Sort divisions alphabetically
    leagues = db.session.query(League).filter(League.org_id == 1).all()
    return render_template('game_shootout.html', divisions=divisions, leagues=leagues)

@game_shootout_bp.route('/get_game_shootout_data', methods=['POST'])
def get_game_shootout_data():
    x_axis = request.json.get('x_axis')
    plot_level = request.json.get('plot_level')
    league_number = request.json.get('league_number')

    # Query games without grouping
    query = db.session.query(
        Game.game_number.label('game_id'),
        Game.date,
        db.cast(db.extract('year', Game.date), db.Integer).label('year'),
        db.cast(db.extract('month', Game.date), db.Integer).label('month'),
        Season.season_number,
        Game.home_final_score,
        Game.visitor_final_score,
        Game.home_period_1_score,
        Game.home_period_2_score,
        Game.home_period_3_score,
        Game.visitor_period_1_score,
        Game.visitor_period_2_score,
        Game.visitor_period_3_score,
        Game.visitor_so_shots,
        Game.home_so_shots,
        Game.game_type
    ).join(Division, Game.division_id == Division.id
    ).join(Season, and_(Division.season_number == Season.season_number, Division.league_number == Season.league_number))

    # # Remove old sharksice seasons where we got no scores as of now (broken data at some point or crawl)
    # org_name = current_app.config['ORG_NAME']
    # if (org_name == 'sharksice' and league_number == '1'):
    #     query = query.filter(Season.season_number >= 22)
    
    if plot_level != 'all':
        query = query.filter(Division.level == plot_level)
    query = query.filter(Division.league_number == league_number)

    # Filter out games where home_final_score or visitor_final_score is NULL
    query = query.filter(Game.home_final_score.isnot(None), Game.visitor_final_score.isnot(None))

    # Filter out games where game_type is 'Playoff' or 'Championship'
    query = query.filter(~Game.game_type.in_(['Playoff', 'Championship']))

    games = query.all()

    # Convert to DataFrame
    df = pd.DataFrame([(g.game_id, g.year, g.month, g.season_number, g.home_final_score, g.visitor_final_score, g.home_period_1_score, g.home_period_2_score, g.home_period_3_score, g.visitor_period_1_score, g.visitor_period_2_score, g.visitor_period_3_score, g.visitor_so_shots, g.home_so_shots, g.game_type) for g in games],
                      columns=['game_id', 'year', 'month', 'season_number', 'home_final_score', 'visitor_final_score', 'home_period_1_score', 'home_period_2_score', 'home_period_3_score', 'visitor_period_1_score', 'visitor_period_2_score', 'visitor_period_3_score', 'visitor_so_shots', 'home_so_shots', 'game_type'])

    if df.empty:
        return jsonify({'x': [], 'y': {}})

    # Mark year_month and season for each data point
    df['year_month'] = df['year'].astype(str) + '/' + df['month'].astype(str).str.zfill(2)

    # Calculate the required scores
    df['regulation_home_score'] = df['home_period_1_score'] + df['home_period_2_score'] + df['home_period_3_score']
    df['regulation_visitor_score'] = df['visitor_period_1_score'] + df['visitor_period_2_score'] + df['visitor_period_3_score']
    df['is_tie'] = df['regulation_home_score'] == df['regulation_visitor_score']
    df['so_shots_present'] = (df['visitor_so_shots'] + df['home_so_shots']) > 0

    df['went_to_so'] = (df['regulation_home_score'] != df['home_final_score']) | (df['regulation_visitor_score'] != df['visitor_final_score']) | (df['so_shots_present'])

    # Group by the selected x_axis
    if x_axis == 'year_month':
        df_grouped = df.groupby('year_month')
    else:
        df_grouped = df.groupby('season_number')

    # Perform calculations for each group
    total_games = df_grouped.size()
    tie_games = df_grouped['is_tie'].sum()
    shootout_games = df_grouped.apply(lambda x: (x['is_tie'] & x['went_to_so']).sum())

    # Remove rows where total_games is zero
    valid_indices = total_games[total_games > 0].index
    total_games = total_games[valid_indices]
    tie_games = tie_games[valid_indices]
    shootout_games = shootout_games[valid_indices]

    tie_percentage = (tie_games / total_games) * 100
    shootout_percentage = (shootout_games / tie_games).replace([float('inf'), -float('inf')], 0).fillna(0) * 100

    # Get season names for the selected league_number
    season_names = db.session.query(Season.season_number, Season.season_name).filter(Season.league_number == league_number).all()
    season_name_dict = {season.season_number: season.season_name for season in season_names}

    # Replace season_number with season_name for display
    if x_axis == 'year_month':
        x_for_ordering = total_games.index.tolist()
    else:
        x_names_for_display = total_games.index.tolist()
        x_display_names = [season_name_dict[season_number] for season_number in x_names_for_display]
        x_for_ordering = [season_number for season_number in x_names_for_display]

    result = {
        'x': x_for_ordering,
        'y': {
            'Tied after 3rd': tie_percentage.tolist(),
            'Shootout when tied': shootout_percentage.tolist()
        },
        'season_names': x_display_names if x_axis != 'year_month' else []
    }

    return jsonify(result)