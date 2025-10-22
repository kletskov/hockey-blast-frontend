from flask import Blueprint, render_template, request, jsonify, url_for
from hockey_blast_common_lib.models import db, Organization, Game, Team, Division
from hockey_blast_common_lib.stats_utils import ALL_ORGS_ID
from datetime import datetime, date

games_bp = Blueprint('games', __name__)

DEFAULT_TOP_N = 50
MAX_TOP_N = 2000

@games_bp.route('/games', methods=['GET'])
def games():
    organizations = db.session.query(Organization).all()
    top_n = request.args.get('top_n', default=DEFAULT_TOP_N)
    org_id = request.args.get('org_id')
    level_id = request.args.get('level_id')
    season_id = request.args.get('season_id')
    game_status = request.args.get('game_status', 'completed')
    location = request.args.get('location')
    team_id = request.args.get('team_id')
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

    return render_template('games.html', organizations=organizations, top_n=top_n, org_id=org_id, level_id=level_id, season_id=season_id, game_status=game_status, location=location, team_id=team_id)

@games_bp.route('/filter_games', methods=['POST'])
def filter_games():
    org_id = request.json.get('org_id')
    level_id = request.json.get('level_id')
    season_id = request.json.get('season_id')
    top_n = request.json.get('top_n', DEFAULT_TOP_N)
    game_status = request.json.get('game_status', 'completed')
    location = request.json.get('location')
    team_id = request.json.get('team_id')
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

    try:
        level_id = int(level_id)
    except (ValueError, TypeError):
        level_id = None

    try:
        season_id = int(season_id)
    except (ValueError, TypeError):
        season_id = None

    try:
        team_id = int(team_id)
    except (ValueError, TypeError):
        team_id = None

    if org_id != ALL_ORGS_ID:
        query = query.filter(Game.org_id == org_id)

    if game_status == 'completed':
        query = query.filter(Game.status.ilike("Final%")).order_by(Game.date.desc(), Game.time.desc())
    elif game_status == 'scheduled':
        today = date.today()
        query = query.filter(~Game.status.ilike("Final%"), Game.date >= today).order_by(Game.date.asc(), Game.time.asc())
    elif game_status == 'all':
        query = query.order_by(Game.date.desc(), Game.time.desc())

    if level_id:
        query = query.join(Division, Game.division_id == Division.id).filter(Division.level_id == level_id)
    if season_id:
        query = query.filter(Division.season_id == season_id)
    if location:
        query = query.filter(Game.location.ilike(f"%{location}%"))
    if team_id:
        query = query.filter((Game.home_team_id == team_id) | (Game.visitor_team_id == team_id))

    games = query.limit(top_n).all()

    games_data = []
    team_stats = {
        'GP': 0,
        'W': 0,
        'L': 0,
        'T': 0,
        'OTL': 0
    }
    
    # Day of week mapping to match human_stats format
    day_of_week_map = {1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat', 7: 'Sun'}

    for game in games:
        if game.home_team_id is None or game.visitor_team_id is None:
            continue

        visitor_team = db.session.query(Team).filter(Team.id == game.visitor_team_id).first()
        home_team = db.session.query(Team).filter(Team.id == game.home_team_id).first()

        if game.status.startswith('Final'):
            home_period_scores = (game.home_period_1_score or 0) + (game.home_period_2_score or 0) + (game.home_period_3_score or 0)
            visitor_period_scores = (game.visitor_period_1_score or 0) + (game.visitor_period_2_score or 0) + (game.visitor_period_3_score or 0)

            if game.home_team_id == team_id:
                if game.home_final_score > game.visitor_final_score:
                    color = "#7CFC00"
                    team_stats['W'] += 1
                elif game.home_final_score < game.visitor_final_score:
                    if visitor_period_scores == game.visitor_final_score:
                        team_stats['L'] += 1
                    else:
                        team_stats['OTL'] += 1
                    color = "red"
                else:
                    team_stats['T'] += 1
                    color = "black"
                final_score = f"<span style='color:black;'>{game.visitor_final_score}</span> : <strong style='color:{color};'>{game.home_final_score}</strong>"
            elif game.visitor_team_id == team_id:
                if game.visitor_final_score > game.home_final_score:
                    color = "#7CFC00"
                    team_stats['W'] += 1
                elif game.visitor_final_score < game.home_final_score:
                    if home_period_scores == game.home_final_score:
                        team_stats['L'] += 1
                    else:
                        team_stats['OTL'] += 1
                    color = "red"
                else:
                    team_stats['T'] += 1
                    color = "black"
                final_score = f"<strong style='color:{color};'>{game.visitor_final_score}</strong> : <span style='color:black;'>{game.home_final_score}</span>"
            else:
                final_score = f"<span style='color:black;'>{game.visitor_final_score}</span> : <span style='color:black;'>{game.home_final_score}</span>"
        else:
            final_score = "TBD"

        if game.home_team_id == team_id:
            team_names = f"<a href='{url_for('team_stats.team_stats', team_id=visitor_team.id)}'>{visitor_team.name}</a> at <strong><a href='{url_for('team_stats.team_stats', team_id=home_team.id)}'>{home_team.name}</a></strong>"
        elif game.visitor_team_id == team_id:
            team_names = f"<strong><a href='{url_for('team_stats.team_stats', team_id=visitor_team.id)}'>{visitor_team.name}</a></strong> at <a href='{url_for('team_stats.team_stats', team_id=home_team.id)}'>{home_team.name}</a>"
        else:
            team_names = f"<a href='{url_for('team_stats.team_stats', team_id=visitor_team.id)}'>{visitor_team.name}</a> at <a href='{url_for('team_stats.team_stats', team_id=home_team.id)}'>{home_team.name}</a>"

        day_of_week = day_of_week_map.get(game.day_of_week, '')
        date_time = f"{day_of_week} {game.date.strftime('%m/%d/%y')} {game.time.strftime('%I:%M%p')}"
        
        games_data.append({
            'id': game.id,
            'date': date_time,
            'time': game.time.strftime('%I:%M%p'),
            'final_score': final_score,
            'team_names': team_names,
            'location': game.location,
            'status': game.status
        })

        team_stats['GP'] += 1

    return jsonify({
        'games': games_data,
        'team_stats': team_stats
    })