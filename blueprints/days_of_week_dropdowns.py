from flask import Blueprint, request, jsonify
from hockey_blast_common_lib.models import db, Level, Season

days_of_week_dropdowns_bp = Blueprint('days_of_week_dropdowns', __name__)

@days_of_week_dropdowns_bp.route('/filter_levels', methods=['POST'])
def filter_levels():
    org_id = request.json.get('org_id')
    try:
        org_id = int(org_id)
    except (ValueError, TypeError):
        return jsonify([])

    query = db.session.query(Level).filter(
        Level.org_id == org_id,
        Level.level_name.ilike('Adult Division%')
    )

    levels = query.all()
    levels_data = [{'id': level.id, 'level_name': level.level_name} for level in levels]
    return jsonify(levels_data)

@days_of_week_dropdowns_bp.route('/filter_seasons', methods=['POST'])
def filter_seasons():
    query = db.session.query(Season).filter(
        Season.org_id == 1,
        Season.league_number == 1
    ).order_by(Season.season_number.desc())
    seasons = query.all()
    seasons_data = [{'id': season.id, 'season_name': season.season_name} for season in seasons]
    return jsonify(seasons_data)