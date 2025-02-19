import logging
from flask import Blueprint, render_template, request, jsonify, url_for
from hockey_blast_common_lib.models import db, Organization, Level, Division, Season, Team, Human, Game, GameRoster
from hockey_blast_common_lib.stats_models import OrgStatsSkater, LevelStatsSkater, DivisionStatsSkater
from hockey_blast_common_lib.stats_utils import ALL_ORGS_ID
from .skater_performance_dropdowns import filter_levels, filter_seasons, filter_teams, get_levels_for_skater_in_org, get_divisions_and_seasons
from .team_division_skater_stats import team_division_skater_stats_bp, compute_skater_stats
import re
from datetime import datetime

skater_performance_bp = Blueprint('skater_performance', __name__)
skater_performance_bp.register_blueprint(team_division_skater_stats_bp, url_prefix='/team_division_skater_stats')

def format_rank_percentile(rank, total):
    percentile = (total - rank) / total * 100
    return f"{rank}/{total}<br>{percentile:.0f}th"

def append_skater_performance_result(skater_performance_results, stats, context):
    if isinstance(stats, dict):
        human_id = stats.get('human_id')
        first_game_id = stats.get('first_game_id')
        last_game_id = stats.get('last_game_id')
        points_per_game = stats.get('points_per_game')
        points_per_game_rank = stats.get('points_per_game_rank')
        games_played = stats.get('games_played')
        games_played_rank = stats.get('games_played_rank')
        goals_per_game = stats.get('goals_per_game')
        goals_per_game_rank = stats.get('goals_per_game_rank')
        assists_per_game = stats.get('assists_per_game')
        assists_per_game_rank = stats.get('assists_per_game_rank')
        penalties_per_game = stats.get('penalties_per_game')
        penalties_per_game_rank = stats.get('penalties_per_game_rank')
        gm_penalties_per_game = stats.get('gm_penalties_per_game')
        gm_penalties_per_game_rank = stats.get('gm_penalties_per_game_rank')
    else:
        human_id = stats.human_id
        first_game_id = stats.first_game_id
        last_game_id = stats.last_game_id
        points_per_game = stats.points_per_game
        points_per_game_rank = stats.points_per_game_rank
        games_played = stats.games_played
        games_played_rank = stats.games_played_rank
        goals_per_game = stats.goals_per_game
        goals_per_game_rank = stats.goals_per_game_rank
        assists_per_game = stats.assists_per_game
        assists_per_game_rank = stats.assists_per_game_rank
        penalties_per_game = stats.penalties_per_game
        penalties_per_game_rank = stats.penalties_per_game_rank
        gm_penalties_per_game = stats.gm_penalties_per_game
        gm_penalties_per_game_rank = stats.gm_penalties_per_game_rank

    first_game = db.session.query(Game.date).filter(Game.id == first_game_id).first() if first_game_id else None
    last_game = db.session.query(Game.date).filter(Game.id == last_game_id).first() if last_game_id else None
    skater_performance_results.append({
        'human_id': human_id,
        'context': context,
        'points_per_game': f"{points_per_game:.2f}",
        'points_per_game_rank': format_rank_percentile(points_per_game_rank, stats['total_in_rank'] if isinstance(stats, dict) else stats.total_in_rank),
        'games_played': games_played,
        'games_played_rank': format_rank_percentile(games_played_rank, stats['total_in_rank'] if isinstance(stats, dict) else stats.total_in_rank),
        'goals_per_game': f"{goals_per_game:.2f}",
        'goals_per_game_rank': format_rank_percentile(goals_per_game_rank, stats['total_in_rank'] if isinstance(stats, dict) else stats.total_in_rank),
        'assists_per_game': f"{assists_per_game:.2f}",
        'assists_per_game_rank': format_rank_percentile(assists_per_game_rank, stats['total_in_rank'] if isinstance(stats, dict) else stats.total_in_rank),
        'penalties_per_game': f"{penalties_per_game:.2f}",
        'penalties_per_game_rank': format_rank_percentile(penalties_per_game_rank, stats['total_in_rank'] if isinstance(stats, dict) else stats.total_in_rank),
        'gm_penalties_per_game': f"{gm_penalties_per_game:.2f}",
        'gm_penalties_per_game_rank': format_rank_percentile(gm_penalties_per_game_rank, stats['total_in_rank'] if isinstance(stats, dict) else stats.total_in_rank),
        'first_game': f"<a href='{url_for('game_card.game_card', game_id=first_game_id)}'>{first_game.date.strftime('%m/%d/%y')}</a>" if first_game else None,
        'last_game': f"<a href='{url_for('game_card.game_card', game_id=last_game_id)}'>{last_game.date.strftime('%m/%d/%y')}</a>" if last_game else None
    })

def extract_date_from_link(link):
    match = re.search(r'>(\d{2}/\d{2}/\d{2})<', link)
    if match:
        return datetime.strptime(match.group(1), '%m/%d/%y')
    return None

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

    try:
        human_id = int(human_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid human_id'}), 400

    skater_performance_results = []
    team_performance_results = []
    all_skaters_results = []
    level_name = ""
    season_name = ""

    if org_id == ALL_ORGS_ID:
        org_stats = db.session.query(OrgStatsSkater).filter(
            OrgStatsSkater.human_id == human_id
        ).order_by(OrgStatsSkater.org_id).limit(top_n).all()

        for stats in org_stats:
            organization = db.session.query(Organization).filter(Organization.id == stats.org_id).first()
            context = f'<a href="{organization.website}">{organization.organization_name}</a>'
            append_skater_performance_result(skater_performance_results, stats, context)
    else:
        if level_id is None:
            levels = get_levels_for_skater_in_org(org_id, human_id)
            for level in levels:
                level_stats = db.session.query(LevelStatsSkater).filter(
                    LevelStatsSkater.level_id == level.id,
                    LevelStatsSkater.human_id == human_id
                ).order_by(LevelStatsSkater.points_per_game_rank).limit(top_n).all()

                for stats in level_stats:
                    context = level.level_name
                    append_skater_performance_result(skater_performance_results, stats, context)
        else:
            if season_id is None:
                divisions, seasons = get_divisions_and_seasons(org_id, level_id, human_id)
                for division in divisions:
                    division_stats = db.session.query(DivisionStatsSkater).filter(
                        DivisionStatsSkater.division_id == division.id,
                        DivisionStatsSkater.human_id == human_id
                    ).order_by(DivisionStatsSkater.points_per_game_rank).limit(top_n).all()

                    for stats in division_stats:
                        season = next((s for s in seasons if s.id == division.season_id), None)
                        context = season.season_name if season else "Unknown Season"
                        append_skater_performance_result(skater_performance_results, stats, context)
            else:
                # Fetch the unique division_id using org_id, season_id, and level_id
                division = db.session.query(Division.id).filter(
                    Division.org_id == org_id,
                    Division.season_id == season_id,
                    Division.level_id == level_id
                ).first()

                if division:
                    division_id = division.id

                if team_id is None:
                    # Fetch level and season names
                    level = db.session.query(Level).filter(Level.id == level_id).first()
                    season = db.session.query(Season).filter(Season.id == season_id).first()
                    level_name = level.level_name if level else ""
                    season_name = season.season_name if season else ""

                    # Fetch all skaters for the selected division and season
                    all_skaters_stats = db.session.query(DivisionStatsSkater).filter(
                        DivisionStatsSkater.division_id == division_id
                    ).order_by(DivisionStatsSkater.points_per_game_rank).all()

                    for stats in all_skaters_stats:
                        player = db.session.query(Human).filter(Human.id == stats.human_id).first()
                        if player:
                            link_text = f"{player.first_name} {player.middle_name} {player.last_name}".strip()
                            link = f'<a href="{url_for("human_stats.human_stats", human_id=player.id, top_n=20)}">{link_text}</a>'
                            append_skater_performance_result(all_skaters_results, stats, link)
                else:
                    # Fetch team stats in division
                    games = db.session.query(Game.id).filter(
                        Game.division_id == division_id,
                        (Game.home_team_id == team_id) | (Game.visitor_team_id == team_id)
                    ).all()
                    games = [game.id for game in games]

                    # Compute skater stats
                    stats_dict = compute_skater_stats(games, team_id)

                    # Fetch team names for context
                    team = db.session.query(Team).filter(Team.id == team_id).first()
                    context = f'<a href="{url_for("team_stats.team_stats", team_id=team.id)}">{team.name}</a>'

                    # Add team performance results
                    for key, stats in stats_dict.items():
                        player = db.session.query(Human).filter(Human.id == key).first()
                        if player:
                            link_text = f"{player.first_name} {player.middle_name} {player.last_name}".strip()
                            link = f'<a href="{url_for("human_stats.human_stats", human_id=player.id, top_n=20)}">{link_text}</a>'
                            append_skater_performance_result(team_performance_results, stats, link)

    # Sort the results by last game date (descending) and first game date (ascending)
    skater_performance_results.sort(key=lambda x: (x['points_per_game']), reverse=True)
    team_performance_results.sort(key=lambda x: (x['points_per_game']), reverse=True)
    all_skaters_results.sort(key=lambda x: (x['points_per_game']), reverse=True)

    return jsonify({
        'skater_performance': skater_performance_results,
        'team_performance': team_performance_results,
        'all_skaters': all_skaters_results,
        'level_name': level_name,
        'season_name': season_name
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
