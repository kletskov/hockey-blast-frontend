import logging
from flask import Blueprint, render_template, request, jsonify, url_for
from hockey_blast_common_lib.models import db, Organization, Level, Division, Season, Team, Human
from hockey_blast_common_lib.stats_models import OrgStatsSkater, LevelStatsSkater, DivisionStatsSkater
from hockey_blast_common_lib.stats_utils import ALL_ORGS_ID
from .skater_performance_dropdowns import filter_levels, filter_seasons, filter_teams

skater_performance_bp = Blueprint('skater_performance', __name__)

@skater_performance_bp.route('/', methods=['GET'])
def skater_performance():
    human_id = request.args.get('human_id')
    human_name = "Unknown"
    if human_id:
        human = db.session.query(Human).filter(Human.id == human_id).first()
        if human:
            human_name = f"{human.first_name} {human.middle_name} {human.last_name}".strip()
        organizations = db.session.query(Organization).join(OrgStatsSkater, Organization.id == OrgStatsSkater.org_id).filter(OrgStatsSkater.human_id == human_id).all()
    else:
        organizations = db.session.query(Organization).all()
    
    top_n = request.args.get('top_n', default=50, type=int)
    org_id = request.args.get('org_id', type=int)
    level_id = request.args.get('level_id')
    season_id = request.args.get('season_id')
    return render_template('skater_performance.html', organizations=organizations, top_n=top_n, org_id=org_id, level_id=level_id, season_id=season_id, human_id=human_id, human_name=human_name)

@skater_performance_bp.route('/filter_skater_performance', methods=['POST'])
def filter_skater_performance():
    org_id = request.json.get('org_id')
    level_id = request.json.get('level_id')
    season_id = request.json.get('season_id')
    team_id = request.json.get('team_id')
    top_n = request.json.get('top_n', 50)
    human_id = request.json.get('human_id')

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

    skater_performance_results = []

    if org_id == ALL_ORGS_ID:
        org_stats = db.session.query(OrgStatsSkater).filter(
            OrgStatsSkater.human_id == human_id
        ).order_by(OrgStatsSkater.points_per_game_rank).limit(top_n).all()

        for index, stats in enumerate(org_stats, start=1):
            organization = db.session.query(Organization).filter(Organization.id == stats.org_id).first()
            skater_performance_results.append({
                'context': f'<a href="{organization.website}">{organization.organization_name}</a>',
                'points_per_game': stats.points_per_game,
                'points_per_game_rank': stats.points_per_game_rank,
                'games_played': stats.games_played,
                'games_played_rank': stats.games_played_rank
            })
    else:
        if level_id and season_id:
            division = db.session.query(Division).filter(Division.org_id == org_id, Division.level_id == level_id, Division.season_id == season_id).first()
            if not division:
                return jsonify({"error": "Division not found"}), 404
            stats_model = DivisionStatsSkater
            filter_column = 'division_id'
            filter_value = division.id
        elif level_id:
            stats_model = LevelStatsSkater
            filter_column = 'level_id'
            filter_value = level_id
        else:
            stats_model = OrgStatsSkater
            filter_column = 'org_id'
            filter_value = org_id

        skater_performance_data = db.session.query(stats_model).filter(
            getattr(stats_model, filter_column) == filter_value,
            stats_model.human_id == human_id
        ).order_by(stats_model.points_per_game_rank).limit(top_n).all()

        for index, stats in enumerate(skater_performance_data, start=1):
            organization = db.session.query(Organization).filter(Organization.id == org_id).first()
            skater_performance_results.append({
                'context': f'<a href="{organization.website}">{organization.organization_name}</a>',
                'points_per_game': stats.points_per_game,
                'points_per_game_rank': stats.points_per_game_rank,
                'games_played': stats.games_played,
                'games_played_rank': stats.games_played_rank
            })

    return jsonify({
        'skater_performance': skater_performance_results
    })

@skater_performance_bp.route('/filter_levels', methods=['POST'])
def filter_levels_route():
    org_id = request.json.get('org_id')
    human_id = request.json.get('human_id')
    return filter_levels(org_id, human_id)

@skater_performance_bp.route('/filter_seasons', methods=['POST'])
def filter_seasons_route():
    org_id = request.json.get('org_id')
    level_id = request.json.get('level_id')
    human_id = request.json.get('human_id')
    return filter_seasons(org_id, level_id, human_id)

@skater_performance_bp.route('/filter_teams', methods=['POST'])
def filter_teams_route():
    org_id = request.json.get('org_id')
    level_id = request.json.get('level_id')
    season_id = request.json.get('season_id')
    human_id = request.json.get('human_id')
    return filter_teams(org_id, level_id, season_id, human_id)
