from flask import Blueprint, render_template
from hockey_blast_common_lib.models import db, Division, Game, Season, GameRoster
from players_per_season import players_per_season
from blueprints.teams_per_season import teams_per_season

seasons_bp = Blueprint('seasons', __name__)

@seasons_bp.route('/seasons')
def interactive_plot():
    # Perform the query for all seasons
    seasons_results = db.session.query(
        Season.season_number,
        Season.season_name,
        Season.start_date,
        Season.end_date
    ).filter(~Season.season_number.in_([4, 44, 48])).all()

    # Call the existing functions with the seasons data
    players_per_season_content = players_per_season()
    teams_per_season_content = teams_per_season()

    return render_template('seasons.html', players_per_season_content=players_per_season_content, teams_per_season_content=teams_per_season_content)