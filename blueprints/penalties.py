import logging
from flask import Blueprint, render_template, request, jsonify, url_for
from hockey_blast_common_lib.models import db, Organization, Level, Division, Human, Game, GameRoster
from hockey_blast_common_lib.stats_models import OrgStatsSkater, LevelStatsSkater, DivisionStatsSkater
from hockey_blast_common_lib.stats_utils import ALL_ORGS_ID
from datetime import datetime, timedelta

penalties_bp = Blueprint('penalties', __name__)

MIN_GAMES_ORG = 20
MIN_GAMES_LEVEL = 10
MIN_GAMES_DIVISION = 2

# Coefficients for fetching more data in "active" player mode
COEFF_ORG = 50 / 3
COEFF_LEVEL = 50 / 4
COEFF_DIVISION = 50 / 47

ACTIVE_PLAYER_WINDOW = timedelta(days=90)

@penalties_bp.route('/penalties', methods=['GET'])
def penalties():
    organizations = db.session.query(Organization).all()
    top_n = request.args.get('top_n', default=50, type=int)
    org_id = request.args.get('org_id', default=ALL_ORGS_ID, type=int)
    level_id = request.args.get('level_id')
    season_id = request.args.get('season_id')
    penalty_type = request.args.get('penalty_type', 'all')
    player_status = request.args.get('player_status', 'all')
    display_value = request.args.get('display_value', 'per_game')
    return render_template('penalties.html', organizations=organizations, top_n=top_n, org_id=org_id, level_id=level_id, season_id=season_id, penalty_type=penalty_type, player_status=player_status, display_value=display_value)

@penalties_bp.route('/filter_penalties', methods=['POST'])
def filter_penalties():
    org_id = request.json.get('org_id')
    level_id = request.json.get('level_id')
    season_id = request.json.get('season_id')
    team_id = request.json.get('team_id')
    top_n = request.json.get('top_n', 50)
    penalty_type = request.json.get('penalty_type', 'all')
    player_status = request.json.get('player_status', 'all')
    display_value = request.json.get('display_value', 'per_game')

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

    try:
        top_n = int(top_n)
    except (ValueError, TypeError):
        top_n = 20

    top_n_to_fetch = top_n
    if player_status == 'active':
        if level_id and season_id:
            top_n_to_fetch = int(top_n * COEFF_DIVISION)
        elif level_id:
            top_n_to_fetch = int(top_n * COEFF_LEVEL)
        else:
            top_n_to_fetch = int(top_n * COEFF_ORG)

    if level_id and season_id:
        division = db.session.query(Division).filter(Division.org_id == org_id, Division.level_id == level_id, Division.season_id == season_id).first()
        if not division:
            return jsonify({"error": "Division not found"}), 404
        stats_model = DivisionStatsSkater
        filter_column = 'division_id'
        filter_value = division.id
        min_games = MIN_GAMES_DIVISION
    elif level_id:
        stats_model = LevelStatsSkater
        filter_column = 'level_id'
        filter_value = level_id
        min_games = MIN_GAMES_LEVEL
    else:
        stats_model = OrgStatsSkater
        filter_column = 'org_id'
        filter_value = org_id
        min_games = MIN_GAMES_ORG

    if team_id:
        # Fetch all GameRoster entries for the specified org, division, and team
        game_rosters = db.session.query(GameRoster).join(Game, GameRoster.game_id == Game.id).filter(
            Game.org_id == org_id,
            Game.division_id == filter_value,
            GameRoster.team_id == team_id
        ).all()
        human_ids = {roster.human_id for roster in game_rosters}
    else:
        human_ids = None

    if penalty_type == 'gm':
        penalties_data = db.session.query(stats_model, Human).join(Human, stats_model.human_id == Human.id).filter(
            getattr(stats_model, filter_column) == filter_value,
            stats_model.games_participated >= min_games,
            Human.id.in_(human_ids) if human_ids else True
        ).order_by(stats_model.gm_penalties_rank).limit(top_n_to_fetch).all()
        penalties_per_game_data = db.session.query(stats_model, Human).join(Human, stats_model.human_id == Human.id).filter(
            getattr(stats_model, filter_column) == filter_value,
            stats_model.games_participated >= min_games,
            Human.id.in_(human_ids) if human_ids else True
        ).order_by(stats_model.gm_penalties_per_game_rank).limit(top_n_to_fetch).all()
    else:
        penalties_data = db.session.query(stats_model, Human).join(Human, stats_model.human_id == Human.id).filter(
            getattr(stats_model, filter_column) == filter_value,
            stats_model.games_participated >= min_games,
            Human.id.in_(human_ids) if human_ids else True
        ).order_by(stats_model.penalties_rank).limit(top_n_to_fetch).all()
        penalties_per_game_data = db.session.query(stats_model, Human).join(Human, stats_model.human_id == Human.id).filter(
            getattr(stats_model, filter_column) == filter_value,
            stats_model.games_participated >= min_games,
            Human.id.in_(human_ids) if human_ids else True
        ).order_by(stats_model.penalties_per_game_rank).limit(top_n_to_fetch).all()

    if player_status == 'active':
        active_threshold_date = datetime.now() - ACTIVE_PLAYER_WINDOW
        penalties_data = [(stats, human) for stats, human in penalties_data if stats.last_game_id and datetime.combine(db.session.query(Game.date).filter(Game.id == stats.last_game_id).first()[0], datetime.min.time()) >= active_threshold_date]
        penalties_per_game_data = [(stats, human) for stats, human in penalties_per_game_data if stats.last_game_id and datetime.combine(db.session.query(Game.date).filter(Game.id == stats.last_game_id).first()[0], datetime.min.time()) >= active_threshold_date]

    penalties_results = []
    for index, (stats, human) in enumerate(penalties_data[:top_n], start=1):
        if penalty_type == 'gm':
            penalties = stats.gm_penalties
        else:
            penalties = stats.penalties
        if penalties and penalties > 0:
            link_text = f"{human.first_name} {human.middle_name} {human.last_name}".strip()
            link = f'<a href="{url_for("human_stats.human_stats", human_id=human.id, top_n=20)}">{link_text}</a>'
            first_game_link = f"<a href='{url_for('game_card.game_card', game_id=stats.first_game_id)}'>{db.session.query(Game.date).filter(Game.id == stats.first_game_id).first()[0].strftime('%m/%d/%y')}</a>" if stats.first_game_id else None
            last_game_link = f"<a href='{url_for('game_card.game_card', game_id=stats.last_game_id)}'>{db.session.query(Game.date).filter(Game.id == stats.last_game_id).first()[0].strftime('%m/%d/%y')}</a>" if stats.last_game_id else None
            penalties_results.append({
                'rank': index,
                'name': link,
                'penalties': penalties,
                'first_game_link': first_game_link,
                'last_game_link': last_game_link
            })

    penalties_per_game_results = []
    for index, (stats, human) in enumerate(penalties_per_game_data[:top_n], start=1):
        if penalty_type == 'gm':
            penalties_per_game = stats.gm_penalties_per_game
        else:
            penalties_per_game = stats.penalties_per_game
        if penalties_per_game and penalties_per_game > 0:
            link_text = f"{human.first_name} {human.middle_name} {human.last_name}".strip()
            link = f'<a href="{url_for("human_stats.human_stats", human_id=human.id, top_n=20)}">{link_text}</a>'
            first_game_link = f"<a href='{url_for('game_card.game_card', game_id=stats.first_game_id)}'>{db.session.query(Game.date).filter(Game.id == stats.first_game_id).first()[0].strftime('%m/%d/%y')}</a>" if stats.first_game_id else None
            last_game_link = f"<a href='{url_for('game_card.game_card', game_id=stats.last_game_id)}'>{db.session.query(Game.date).filter(Game.id == stats.last_game_id).first()[0].strftime('%m/%d/%y')}</a>" if stats.last_game_id else None
            penalties_per_game_results.append({
                'rank': index,
                'name': link,
                'penalties_per_game': penalties_per_game,
                'first_game_link': first_game_link,
                'last_game_link': last_game_link
            })

    return jsonify({
        'penalties': penalties_results,
        'penalties_per_game': penalties_per_game_results
    })
