from flask import Blueprint, jsonify, request
from hockey_blast_common_lib.models import Division, League, Level, Season, db

days_of_week_dropdowns_bp = Blueprint("days_of_week_dropdowns", __name__)


@days_of_week_dropdowns_bp.route("/filter_leagues", methods=["POST"])
def filter_leagues():
    org_id = request.json.get("org_id")
    try:
        org_id = int(org_id)
    except (ValueError, TypeError):
        return jsonify([])

    leagues = (
        db.session.query(League)
        .filter(League.org_id == org_id)
        .order_by(League.league_name)
        .all()
    )
    return jsonify([{"id": l.id, "league_name": l.league_name} for l in leagues])


@days_of_week_dropdowns_bp.route("/filter_levels", methods=["POST"])
def filter_levels():
    org_id = request.json.get("org_id")
    league_id = request.json.get("league_id")
    season_id = request.json.get("season_id")

    try:
        org_id = int(org_id) if org_id else None
    except (ValueError, TypeError):
        org_id = None
    try:
        league_id = int(league_id) if league_id else None
    except (ValueError, TypeError):
        league_id = None
    try:
        season_id = int(season_id) if season_id else None
    except (ValueError, TypeError):
        season_id = None

    # Find level_ids that appear in divisions scoped to this league/season
    query = db.session.query(Division.level_id).distinct()
    if season_id:
        query = query.filter(Division.season_id == season_id)
    elif league_id:
        query = query.join(Season, Division.season_id == Season.id).filter(
            Season.league_id == league_id
        )
    elif org_id:
        query = query.filter(Division.org_id == org_id)

    level_ids = [row[0] for row in query.all() if row[0] is not None]

    level_query = db.session.query(Level).filter(
        Level.level_name.ilike("Adult Division%"),
        Level.id.in_(level_ids),
    )
    if org_id:
        level_query = level_query.filter(Level.org_id == org_id)

    levels = level_query.order_by(Level.level_name).all()
    return jsonify([{"id": l.id, "level_name": l.level_name} for l in levels])


@days_of_week_dropdowns_bp.route("/filter_seasons", methods=["POST"])
def filter_seasons():
    org_id = request.json.get("org_id")
    league_id = request.json.get("league_id")

    try:
        org_id = int(org_id) if org_id else 1
    except (ValueError, TypeError):
        org_id = 1
    try:
        league_id = int(league_id) if league_id else None
    except (ValueError, TypeError):
        league_id = None

    query = db.session.query(Season).filter(Season.org_id == org_id)
    if league_id:
        query = query.filter(Season.league_id == league_id)

    seasons = query.order_by(Season.season_number.desc()).all()
    return jsonify([{"id": s.id, "season_name": s.season_name} for s in seasons])
