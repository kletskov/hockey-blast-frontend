from flask import Blueprint, jsonify, request
from hockey_blast_common_lib.models import (Division, Game, Level,
                                            Organization, Season, Team, db)
from hockey_blast_common_lib.stats_models import LevelStatsHuman
from hockey_blast_common_lib.stats_utils import ALL_ORGS_ID
from hockey_blast_common_lib.utils import get_fake_level

dropdowns_bp = Blueprint("dropdowns", __name__)


@dropdowns_bp.route("/filter_levels", methods=["POST"])
def filter_levels():
    org_id = request.json.get("org_id")
    level_starts_with = request.json.get("level_starts_with")
    try:
        org_id = int(org_id)
    except (ValueError, TypeError):
        org_id = ALL_ORGS_ID

    if org_id == ALL_ORGS_ID:
        return jsonify([])  # Return an empty list if org_id is ALL_ORGS_ID

    fake_level = get_fake_level(db.session)
    query = (
        db.session.query(Level)
        .join(LevelStatsHuman, Level.id == LevelStatsHuman.level_id)
        .filter(
            Level.org_id == org_id,
            Level.id != fake_level.id,
            # Exclude levels where all stats fields are zero or null
            LevelStatsHuman.games_total > 0,
            # Exclude levels with empty level_name
            Level.level_name.isnot(None),
            Level.level_name != "",
        )
    )

    if level_starts_with:
        query = query.filter(Level.level_name.ilike(f"{level_starts_with}%"))

    levels = query.distinct(Level.id).all()

    levels_data = [{"id": level.id, "level_name": level.level_name} for level in levels]
    return jsonify(levels_data)


@dropdowns_bp.route("/filter_seasons", methods=["POST"])
def filter_seasons():
    org_id = request.json.get("org_id")
    level_id = request.json.get("level_id")
    try:
        org_id = int(org_id)
    except (ValueError, TypeError):
        org_id = ALL_ORGS_ID

    if org_id == ALL_ORGS_ID:
        return jsonify([])  # Return an empty list if org_id is ALL_ORGS_ID

    divisions = (
        db.session.query(Division)
        .filter(Division.org_id == org_id, Division.level_id == level_id)
        .all()
    )
    season_ids = [division.season_id for division in divisions]
    seasons = (
        db.session.query(Season)
        .filter(Season.id.in_(season_ids))
        .order_by(Season.season_number.desc())
        .all()
    )
    seasons_data = [
        {"id": season.id, "season_name": season.season_name} for season in seasons
    ]
    return jsonify(seasons_data)


@dropdowns_bp.route("/organizations", methods=["GET"])
def get_organizations():
    organizations = db.session.query(Organization).all()
    all_orgs = (
        db.session.query(Organization).filter(Organization.id == ALL_ORGS_ID).first()
    )
    if all_orgs:
        organizations.insert(0, all_orgs)
    organizations_data = [
        {"id": org.id, "organization_name": org.organization_name}
        for org in organizations
    ]
    return jsonify(organizations_data)


@dropdowns_bp.route("/filter_teams", methods=["POST"])
def filter_teams():
    org_id = request.json.get("org_id")
    level_id = request.json.get("level_id")
    season_id = request.json.get("season_id")
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

    if org_id == ALL_ORGS_ID:
        return jsonify([])  # Return an empty list if org_id is ALL_ORGS_ID

    division = (
        db.session.query(Division)
        .filter(
            Division.org_id == org_id,
            Division.level_id == level_id,
            Division.season_id == season_id,
        )
        .first()
    )
    if not division:
        return jsonify([])  # Return an empty list if division is not found

    games = db.session.query(Game).filter(Game.division_id == division.id).all()
    team_ids = set()
    for game in games:
        team_ids.add(game.home_team_id)
        team_ids.add(game.visitor_team_id)

    teams = db.session.query(Team).filter(Team.id.in_(team_ids)).all()
    teams_data = [{"id": team.id, "team_name": team.name} for team in teams]
    return jsonify(teams_data)
