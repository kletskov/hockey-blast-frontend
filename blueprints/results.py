from flask import Blueprint, render_template, request, jsonify
from hockey_blast_common_lib.models import db, Organization, Division, Season, Game, Level, Team

results_bp = Blueprint('results', __name__)

@results_bp.route('/results', methods=['GET'])
def results():
    organizations = db.session.query(Organization).all()
    top_n = request.args.get('top_n', default=50, type=int)
    return render_template('results.html', organizations=organizations, top_n=top_n)

@results_bp.route('/filter_levels', methods=['POST'])
def filter_levels():
    org_id = request.json.get('org_id')
    levels = db.session.query(Level).filter(Level.org_id == org_id).distinct(Level.id).all()
    levels_data = [{'id': level.id, 'level_name': level.level_name} for level in levels]
    return jsonify(levels_data)

@results_bp.route('/filter_seasons', methods=['POST'])
def filter_seasons():
    org_id = request.json.get('org_id')
    level_id = request.json.get('level_id')
    divisions = db.session.query(Division).filter(Division.org_id == org_id, Division.level_id == level_id).all()
    season_ids = [division.season_id for division in divisions]
    seasons = db.session.query(Season).filter(Season.id.in_(season_ids)).order_by(Season.season_number.desc()).all()
    seasons_data = [{'id': season.id, 'season_name': season.season_name} for season in seasons]
    return jsonify(seasons_data)

@results_bp.route('/filter_games', methods=['POST'])
def filter_games():
    org_id = request.json.get('org_id')
    level_id = request.json.get('level_id')
    season_id = request.json.get('season_id')
    top_n = request.json.get('top_n', 50)

    query = db.session.query(Game).filter(Game.org_id == org_id, Game.status.startswith("Final"))

    if level_id:
        query = query.join(Division, Game.division_id == Division.id).filter(Division.level_id == level_id)
    if season_id:
        query = query.filter(Division.season_id == season_id)

    games = query.order_by(Game.date.desc(), Game.time.desc()).limit(top_n).all()

    games_data = []
    for game in games:
        visitor_team = db.session.query(Team).filter(Team.id == game.visitor_team_id).first()
        home_team = db.session.query(Team).filter(Team.id == game.home_team_id).first()
        games_data.append({
            'id': game.id,
            'date': game.date.strftime('%m/%d/%Y'),
            'time': game.time.strftime('%I:%M %p'),
            'visitor_team': visitor_team.name,
            'visitor_team_id': visitor_team.id,
            'home_team': home_team.name,
            'home_team_id': home_team.id,
            'visitor_score': game.visitor_final_score,
            'home_score': game.home_final_score
        })

    return jsonify(games_data)
