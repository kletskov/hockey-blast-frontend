from flask import Blueprint, render_template, request, jsonify
from hockey_blast_common_lib.models import db, Organization, Game, Team, Division
from hockey_blast_common_lib.stats_utils import ALL_ORGS_ID
from datetime import datetime, date

games_bp = Blueprint('games', __name__)

DEFAULT_TOP_N = 50
MAX_TOP_N = 200

@games_bp.route('/games', methods=['GET'])
def games():
    organizations = db.session.query(Organization).all()
    top_n = request.args.get('top_n', default=DEFAULT_TOP_N)
    org_id = request.args.get('org_id')
    level_id = request.args.get('level_id')
    season_id = request.args.get('season_id')
    game_status = request.args.get('game_status', 'completed')
    location = request.args.get('location')
    try:
        top_n = int(top_n)
    except ValueError:
        top_n = DEFAULT_TOP_N
    if top_n > MAX_TOP_N:
        top_n = MAX_TOP_N

    try:
        org_id = int(org_id)
    except (ValueError, TypeError):
        org_id = ALL_ORGS_ID

    return render_template('games.html', organizations=organizations, top_n=top_n, org_id=org_id, level_id=level_id, season_id=season_id, game_status=game_status, location=location)

@games_bp.route('/filter_games', methods=['POST'])
def filter_games():
    org_id = request.json.get('org_id')
    level_id = request.json.get('level_id')
    season_id = request.json.get('season_id')
    top_n = request.json.get('top_n', DEFAULT_TOP_N)
    game_status = request.json.get('game_status', 'completed')
    location = request.json.get('location')
    try:
        top_n = int(top_n)
    except ValueError:
        top_n = DEFAULT_TOP_N
    if top_n > MAX_TOP_N:
        top_n = MAX_TOP_N

    query = db.session.query(Game)

    try:
        org_id = int(org_id)
    except (ValueError, TypeError):
        org_id = ALL_ORGS_ID

    if org_id != ALL_ORGS_ID:
        query = query.filter(Game.org_id == org_id)

    if game_status == 'completed':
        query = query.filter(Game.status.ilike("Final%")).order_by(Game.date.desc(), Game.time.desc())
    else:
        today = date.today()
        query = query.filter(~Game.status.ilike("Final%"), Game.date >= today).order_by(Game.date.asc(), Game.time.asc())

    if level_id:
        query = query.join(Division, Game.division_id == Division.id).filter(Division.level_id == level_id)
    if season_id:
        query = query.filter(Division.season_id == season_id)
    if location:
        query = query.filter(Game.location.ilike(f"%{location}%"))

    games = query.limit(top_n).all()

    games_data = []
    for game in games:
        visitor_team = db.session.query(Team).filter(Team.id == game.visitor_team_id).first()
        home_team = db.session.query(Team).filter(Team.id == game.home_team_id).first()
        games_data.append({
            'id': game.id,
            'date': game.date.strftime('%m/%d/%y'),
            'time': game.time.strftime('%I:%M %p'),
            'visitor_team': visitor_team.name,
            'visitor_team_id': visitor_team.id,
            'home_team': home_team.name,
            'home_team_id': home_team.id,
            'visitor_score': game.visitor_final_score if game.status.lower().startswith("final") else "TBD",
            'home_score': game.home_final_score if game.status.lower().startswith("final") else "TBD",
            'location': game.location,
            'status': game.status
        })

    return jsonify(games_data)
