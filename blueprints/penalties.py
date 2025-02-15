import logging
from flask import Blueprint, render_template, request, jsonify, url_for
from hockey_blast_common_lib.models import db, Organization, Level, Division, Human, Game
from hockey_blast_common_lib.stats_models import OrgStatsSkater, LevelStatsSkater, DivisionStatsSkater
from hockey_blast_common_lib.stats_utils import ALL_ORGS_ID

penalties_bp = Blueprint('penalties', __name__)

MIN_GAMES_ORG = 20
MIN_GAMES_LEVEL = 10
MIN_GAMES_DIVISION = 2

@penalties_bp.route('/penalties', methods=['GET'])
def penalties():
    organizations = db.session.query(Organization).all()
    top_n = request.args.get('top_n', default=50, type=int)
    org_id = request.args.get('org_id', default=ALL_ORGS_ID, type=int)
    level_id = request.args.get('level_id')
    season_id = request.args.get('season_id')
    penalty_type = request.args.get('penalty_type', 'all')
    return render_template('penalties.html', organizations=organizations, top_n=top_n, org_id=org_id, level_id=level_id, season_id=season_id, penalty_type=penalty_type)

@penalties_bp.route('/filter_penalties', methods=['POST'])
def filter_penalties():
    org_id = request.json.get('org_id')
    level_id = request.json.get('level_id')
    season_id = request.json.get('season_id')
    top_n = request.json.get('top_n', 50)
    penalty_type = request.json.get('penalty_type', 'all')

    try:
        org_id = int(org_id)
    except (ValueError, TypeError):
        org_id = ALL_ORGS_ID

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

    if penalty_type == 'gm':
        penalties_data = db.session.query(stats_model, Human).join(Human, stats_model.human_id == Human.id).filter(getattr(stats_model, filter_column) == filter_value, stats_model.games_played >= min_games).order_by(stats_model.gm_penalties_rank).limit(top_n).all()
        penalties_per_game_data = db.session.query(stats_model, Human).join(Human, stats_model.human_id == Human.id).filter(getattr(stats_model, filter_column) == filter_value, stats_model.games_played >= min_games).order_by(stats_model.gm_penalties_per_game_rank).limit(top_n).all()
    else:
        penalties_data = db.session.query(stats_model, Human).join(Human, stats_model.human_id == Human.id).filter(getattr(stats_model, filter_column) == filter_value, stats_model.games_played >= min_games).order_by(stats_model.penalties_rank).limit(top_n).all()
        penalties_per_game_data = db.session.query(stats_model, Human).join(Human, stats_model.human_id == Human.id).filter(getattr(stats_model, filter_column) == filter_value, stats_model.games_played >= min_games).order_by(stats_model.penalties_per_game_rank).limit(top_n).all()

    penalties_results = []
    for index, (stats, human) in enumerate(penalties_data, start=1):
        if penalty_type == 'gm':
            penalties = stats.gm_penalties
        else:
            penalties = stats.penalties
        if penalties > 0:
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
    for index, (stats, human) in enumerate(penalties_per_game_data, start=1):
        if penalty_type == 'gm':
            penalties_per_game = stats.gm_penalties_per_game
        else:
            penalties_per_game = stats.penalties_per_game
        if penalties_per_game > 0:
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
