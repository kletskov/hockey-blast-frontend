from flask import Blueprint, request, jsonify
from hockey_blast_common_lib.models import db, Level, Division, Season, Organization
from hockey_blast_common_lib.utils import get_fake_level
from hockey_blast_common_lib.stats_utils import ALL_ORGS_ID

dropdowns_bp = Blueprint('dropdowns', __name__)

@dropdowns_bp.route('/filter_levels', methods=['POST'])
def filter_levels():
    org_id = request.json.get('org_id')
    try:
        org_id = int(org_id)
    except (ValueError, TypeError):
        org_id = ALL_ORGS_ID

    if org_id == ALL_ORGS_ID:
        return jsonify([])  # Return an empty list if org_id is ALL_ORGS_ID

    fake_level = get_fake_level(db.session)
    levels = db.session.query(Level).filter(Level.org_id == org_id, Level.id != fake_level.id).distinct(Level.id).all()
    levels_data = [{'id': level.id, 'level_name': level.level_name} for level in levels]
    return jsonify(levels_data)

@dropdowns_bp.route('/filter_seasons', methods=['POST'])
def filter_seasons():
    org_id = request.json.get('org_id')
    level_id = request.json.get('level_id')
    try:
        org_id = int(org_id)
    except (ValueError, TypeError):
        org_id = ALL_ORGS_ID

    if org_id == ALL_ORGS_ID:
        return jsonify([])  # Return an empty list if org_id is ALL_ORGS_ID

    divisions = db.session.query(Division).filter(Division.org_id == org_id, Division.level_id == level_id).all()
    season_ids = [division.season_id for division in divisions]
    seasons = db.session.query(Season).filter(Season.id.in_(season_ids)).order_by(Season.season_number.desc()).all()
    seasons_data = [{'id': season.id, 'season_name': season.season_name} for season in seasons]
    return jsonify(seasons_data)

@dropdowns_bp.route('/organizations', methods=['GET'])
def get_organizations():
    organizations = db.session.query(Organization).all()
    all_orgs = db.session.query(Organization).filter(Organization.id == ALL_ORGS_ID).first()
    if all_orgs:
        organizations.insert(0, all_orgs)
    organizations_data = [{'id': org.id, 'organization_name': org.organization_name} for org in organizations]
    return jsonify(organizations_data)
