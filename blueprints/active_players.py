from flask import Blueprint, render_template, request, jsonify
from hockey_blast_common_lib.models import db, LevelsMonthly, HumansInLevels, Game, GameRoster, Division, Season
import pandas as pd

active_players_bp = Blueprint('active_players', __name__)

@active_players_bp.route('/active_players')
def interactive_plot():
    levels = db.session.query(LevelsMonthly.level).distinct().all()
    levels = sorted([level[0] for level in levels])  # Sort levels alphabetically
    return render_template('active_players.html', levels=levels)

@active_players_bp.route('/get_plot_data', methods=['POST'])
def get_plot_data():
    x_axis = request.json.get('x_axis')
    plot_1 = request.json.get('plot_1')
    plot_2 = request.json.get('plot_2')
    min_games = int(request.json.get('min_games'))
    print(f"Debug: X Axis: {x_axis}, Plot 1: {plot_1}, Plot 2: {plot_2}, Min Games: {min_games}")
    def get_query(level):
        subquery = db.session.query(
            HumansInLevels.human_id,
            db.func.count(HumansInLevels.levels_monthly_id).label('games_played')
        ).group_by(HumansInLevels.human_id).subquery()

        if x_axis == 'year_month' or x_axis == 'year_over_year':
            query = db.session.query(
                LevelsMonthly.year,
                LevelsMonthly.month,
                db.func.count(HumansInLevels.human_id.distinct()).label('active_players')
            ).join(HumansInLevels, LevelsMonthly.id == HumansInLevels.levels_monthly_id
            ).join(subquery, subquery.c.human_id == HumansInLevels.human_id
            ).filter(subquery.c.games_played >= min_games
            ).group_by(
                LevelsMonthly.year,
                LevelsMonthly.month
            )
            if level != 'all':
                query = query.filter(LevelsMonthly.level == level)
        else:
            query = db.session.query(
                LevelsMonthly.season_number,
                LevelsMonthly.season_name,
                db.func.count(HumansInLevels.human_id.distinct()).label('active_players')
            ).join(HumansInLevels, LevelsMonthly.id == HumansInLevels.levels_monthly_id
            ).join(subquery, subquery.c.human_id == HumansInLevels.human_id
            ).filter(subquery.c.games_played >= min_games
            ).group_by(
                LevelsMonthly.season_number,
                LevelsMonthly.season_name
            )
            if level != 'all':
                query = query.filter(LevelsMonthly.level == level)
        return query

    query_1 = get_query(plot_1)
    query_2 = get_query(plot_2)

    df_1 = pd.read_sql(query_1.statement, db.engine)
    df_2 = pd.read_sql(query_2.statement, db.engine)

    if df_1.empty or df_2.empty:
        return jsonify({'x': [], 'y_1': [], 'y_2': []})

    if x_axis == 'year_month':
        df_1['x'] = df_1['year'].astype(str) + '-' + df_1['month'].astype(str).str.zfill(2)
        df_2['x'] = df_2['year'].astype(str) + '-' + df_2['month'].astype(str).str.zfill(2)
        df_1 = df_1.sort_values('x')
        df_2 = df_2.sort_values('x')
        return jsonify({
            'x': df_1['x'].tolist(),
            'y_1': df_1['active_players'].tolist(),
            'y_2': df_2['active_players'].tolist(),
            'plot_1_name': plot_1,
            'plot_2_name': plot_2
        })
    elif x_axis == 'year_over_year':
        df_1['month'] = df_1['month'].astype(int)
        df_1 = df_1.sort_values(['year', 'month'])
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        years_1 = df_1['year'].unique()
        data_1 = {str(year): df_1[df_1['year'] == year]['active_players'].tolist() for year in years_1}
        return jsonify({
            'months': months,
            'years': data_1,
            'plot_1_name': plot_1
        })
    else:
        df_1 = df_1.sort_values('season_number')
        df_2 = df_2.sort_values('season_number')
        df_1['x'] = df_1['season_name']
        df_2['x'] = df_2['season_name']
        return jsonify({
            'x': df_1['x'].tolist(),
            'y_1': df_1['active_players'].tolist(),
            'y_2': df_2['active_players'].tolist(),
            'plot_1_name': plot_1,
            'plot_2_name': plot_2
        })