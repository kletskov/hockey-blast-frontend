from flask import jsonify
from hockey_blast_common_lib.models import db, Level, Division, Season, Team, GameRoster, Game
from hockey_blast_common_lib.stats_models import DivisionStatsSkater, LevelStatsSkater

def get_levels_for_skater_in_org(org_id, human_id):
    try:
        org_id = int(org_id)
    except (ValueError, TypeError):
        return []

    levels = db.session.query(Level).join(LevelStatsSkater, Level.id == LevelStatsSkater.level_id).filter(
        LevelStatsSkater.human_id == human_id,
        Level.org_id == org_id
    ).all()

    return levels

def get_divisions_and_seasons(org_id, level_id, human_id):
    try:
        org_id = int(org_id)
    except (ValueError, TypeError):
        return [], []

    try:
        level_id = int(level_id)
    except (ValueError, TypeError):
        return [], []

    divisions = db.session.query(Division).join(DivisionStatsSkater, Division.id == DivisionStatsSkater.division_id).filter(
        DivisionStatsSkater.human_id == human_id,
        Division.org_id == org_id,
        Division.level_id == level_id
    ).all()

    season_ids = {division.season_id for division in divisions}
    seasons = db.session.query(Season).filter(Season.id.in_(season_ids)).order_by(Season.season_number.desc()).all()

    return divisions, seasons

def filter_levels(org_id, human_id):
    levels = get_levels_for_skater_in_org(org_id, human_id)
    levels_data = [{'id': level.id, 'level_name': level.level_name} for level in levels]
    return jsonify(levels_data)

def filter_seasons(org_id, level_id, human_id):
    divisions, seasons = get_divisions_and_seasons(org_id, level_id, human_id)
    seasons_data = [{'id': season.id, 'season_name': season.season_name} for season in seasons]
    return jsonify(seasons_data)

def filter_teams(org_id, level_id, season_id, human_id):
    try:
        org_id = int(org_id)
    except (ValueError, TypeError):
        return jsonify([])

    try:
        level_id = int(level_id)
    except (ValueError, TypeError):
        return jsonify([])

    try:
        season_id = int(season_id)
    except (ValueError, TypeError):
        return jsonify([])

    division = db.session.query(Division).filter(
        Division.org_id == org_id,
        Division.level_id == level_id,
        Division.season_id == season_id
    ).first()

    if not division:
        return jsonify([])

    game_rosters = db.session.query(GameRoster).join(Game, GameRoster.game_id == Game.id).filter(
        Game.division_id == division.id,
        GameRoster.human_id == human_id,
        ~GameRoster.role.ilike('g')
    ).all()

    team_ids = {roster.team_id for roster in game_rosters}
    teams = db.session.query(Team).filter(Team.id.in_(team_ids)).all()

    teams_data = [{'id': team.id, 'team_name': team.name} for team in teams]

    return jsonify(teams_data)
