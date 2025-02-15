import logging
from flask import Blueprint, render_template, request, jsonify, url_for
from hockey_blast_common_lib.models import db, Organization, Level, Division, Human
from hockey_blast_common_lib.stats_models import OrgStatsSkater, LevelStatsSkater, DivisionStatsSkater
from hockey_blast_common_lib.stats_utils import ALL_ORGS_ID

penalties_bp = Blueprint('penalties', __name__)

MIN_GAMES_ORG = 20
MIN_GAMES_LEVEL = 10
MIN_GAMES_DIVISION = 2

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@penalties_bp.route('/penalties', methods=['GET'])
def penalties():
    organizations = db.session.query(Organization).all()
    top_n = request.args.get('top_n', default=50, type=int)
    org_id = request.args.get('org_id', default=ALL_ORGS_ID, type=int)
    level_id = request.args.get('level_id')
    season_id = request.args.get('season_id')
    logger.info(f"INITIAL request: org_id={org_id}, level_id={level_id}, season_id={season_id}, top_n={top_n}")
    return render_template('penalties.html', organizations=organizations, top_n=top_n, org_id=org_id, level_id=level_id, season_id=season_id)

@penalties_bp.route('/filter_penalties', methods=['POST'])
def filter_penalties():
    org_id = request.json.get('org_id')
    level_id = request.json.get('level_id')
    season_id = request.json.get('season_id')
    top_n = request.json.get('top_n', 50)

    logger.info(f"Received filter request: org_id={org_id}, level_id={level_id}, season_id={season_id}, top_n={top_n}")

    try:
        org_id = int(org_id)
    except (ValueError, TypeError):
        org_id = ALL_ORGS_ID

    if level_id and season_id:
        division = db.session.query(Division).filter(Division.org_id == org_id, Division.level_id == level_id, Division.season_id == season_id).first()
        if not division:
            logger.error("Division not found")
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

    logger.info(f"Using stats model: {stats_model.__name__}, filter_column={filter_column}, filter_value={filter_value}, min_games={min_games}")

    penalties_data = db.session.query(stats_model, Human).join(Human, stats_model.human_id == Human.id).filter(getattr(stats_model, filter_column) == filter_value, stats_model.games_played >= min_games).order_by(stats_model.penalties_rank).limit(top_n).all()
    penalties_per_game_data = db.session.query(stats_model, Human).join(Human, stats_model.human_id == Human.id).filter(getattr(stats_model, filter_column) == filter_value, stats_model.games_played >= min_games).order_by(stats_model.penalties_per_game_rank).limit(top_n).all()

    logger.info(f"Fetched penalties data: {len(penalties_data)} records")
    logger.info(f"Fetched penalties per game data: {len(penalties_per_game_data)} records")

    penalties_results = []
    for index, (stats, human) in enumerate(penalties_data, start=1):
        link_text = f"{human.first_name} {human.middle_name} {human.last_name}".strip()
        link = f'<a href="{url_for("human_stats.human_stats", human_id=human.id, top_n=20)}">{link_text}</a>'
        penalties_results.append({
            'rank': index,
            'name': link,
            'penalties': stats.penalties
        })

    penalties_per_game_results = []
    for index, (stats, human) in enumerate(penalties_per_game_data, start=1):
        link_text = f"{human.first_name} {human.middle_name} {human.last_name}".strip()
        link = f'<a href="{url_for("human_stats.human_stats", human_id=human.id, top_n=20)}">{link_text}</a>'
        penalties_per_game_results.append({
            'rank': index,
            'name': link,
            'penalties_per_game': stats.penalties_per_game
        })

    return jsonify({
        'penalties': penalties_results,
        'penalties_per_game': penalties_per_game_results
    })
