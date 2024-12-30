from flask import Blueprint, render_template
from flask_table import Table, Col
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
from hockey_blast_common_lib.models import db, Division, Game, Season

teams_per_season_bp = Blueprint('teams_per_season', __name__)

class SeasonItem(object):
    def __init__(self, season_number, season_name, start_date, end_date, num_teams):
        self.season_number = season_number
        self.season_name = season_name
        self.start_date = start_date
        self.end_date = end_date
        self.num_teams = num_teams

@teams_per_season_bp.route('/teams_per_season')
def teams_per_season():
    subquery = db.session.query(
        Game.division_id.label('division_id'),
        Game.home_team_id.label('team_id'),
        Game.id.label('game_id')
    ).union(
        db.session.query(
            Game.division_id.label('division_id'),
            Game.visitor_team_id.label('team_id'),
            Game.id.label('game_id')
        )).subquery()


    filtered_subquery = db.session.query(
        subquery.c.division_id,
        subquery.c.team_id,
        db.func.count(subquery.c.game_id).label('num_games')
    ).group_by(subquery.c.division_id, subquery.c.team_id).having(db.func.count(subquery.c.game_id) > 4).subquery()

    results = db.session.query(
        Season.season_number,
        Season.season_name,
        Season.start_date,
        Season.end_date,
        db.func.count(filtered_subquery.c.team_id.distinct()).label('num_teams')
    ).join(Division, Division.season_number == Season.season_number
    ).join(filtered_subquery, filtered_subquery.c.division_id == Division.id
    ).group_by(Season.season_number, Season.season_name, Season.start_date, Season.end_date).all()

    items = [SeasonItem(result.season_number, result.season_name, result.start_date, result.end_date, result.num_teams) for result in results]

    # Generate plot
    season_names = [item.season_name for item in items]
    num_teams = [item.num_teams for item in items]
    plt.figure(figsize=(20, 10))  # Increase figure size
    plt.plot(season_names, num_teams, marker='o')
    plt.xlabel('Season Name')
    plt.ylabel('Number of Teams')
    plt.title('Number of Teams per Season')
    plt.grid(True)
    plt.xticks(rotation=45, ha='right', fontsize=10)  # Rotate X-axis labels for better readability and adjust font size

    # Annotate each point with the Y-axis value
    for i, txt in enumerate(num_teams):
        plt.annotate(txt, (season_names[i], num_teams[i]), textcoords="offset points", xytext=(0,10), ha='center')

    # Save plot to a string buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plot_url = base64.b64encode(buf.getvalue()).decode('utf8')
    plt.close()

    return render_template('teams_per_season.html', teams_per_season=items, plot_url=plot_url)