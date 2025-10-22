import logging
from flask import Blueprint, render_template, request, jsonify, url_for
from hockey_blast_common_lib.models import db, Organization, Level, Division, Season, Team, Human, Game, ScorekeeperSaveQuality
from hockey_blast_common_lib.stats_models import OrgStatsScorekeeper
from hockey_blast_common_lib.stats_utils import ALL_ORGS_ID
from .scorekeeper_performance_dropdowns import filter_levels, filter_seasons, filter_teams, get_levels_for_scorekeeper_in_org, get_divisions_and_seasons
import re
from datetime import datetime
import json

scorekeeper_performance_bp = Blueprint('scorekeeper_performance', __name__)

def format_rank_percentile(rank, total):
    if not total or total == 0:
        return f"{rank or 0}/{total or 0}<br>N/A"
    percentile = (total - rank) / total * 100
    return f"{rank}/{total}<br>{percentile:.0f}th"

def format_date_link(date, game_id):
    if date:
        date_parts = date.strftime('%m/%d/%y').split('/')
        formatted_date = f"{date_parts[0]}<br>{date_parts[1]}<br>{date_parts[2]}"
        return f"<a href='{url_for('game_card.game_card', game_id=game_id)}'>{formatted_date}</a>"
    return None

def append_scorekeeper_performance_result(scorekeeper_performance_results, stats, context, context_value=0, quality_data=None):
    if isinstance(stats, dict):
        human_id = stats.get('human_id')
        first_game_id = stats.get('first_game_id')
        last_game_id = stats.get('last_game_id')
        games_participated = stats.get('games_participated')
        games_participated_rank = stats.get('games_participated_rank')
        sog_given = stats.get('sog_given')
        sog_given_rank = stats.get('sog_given_rank')
        sog_per_game = stats.get('sog_per_game')
        sog_per_game_rank = stats.get('sog_per_game_rank')
        total_in_rank = stats.get('total_in_rank', 1)
    else:
        human_id = stats.human_id
        first_game_id = stats.first_game_id
        last_game_id = stats.last_game_id
        games_participated = stats.games_participated
        games_participated_rank = stats.games_participated_rank
        sog_given = stats.sog_given
        sog_given_rank = stats.sog_given_rank
        sog_per_game = stats.sog_per_game
        sog_per_game_rank = stats.sog_per_game_rank
        total_in_rank = stats.total_in_rank

    first_game = db.session.query(Game.date).filter(Game.id == first_game_id).first() if first_game_id else None
    last_game = db.session.query(Game.date).filter(Game.id == last_game_id).first() if last_game_id else None

    # Get quality metrics if available
    avg_saves_5sec = 0
    avg_saves_20sec = 0
    max_saves_5sec = 0
    max_saves_20sec = 0
    quality_score = "N/A"

    if quality_data:
        avg_saves_5sec = quality_data.get('avg_saves_5sec', 0)
        avg_saves_20sec = quality_data.get('avg_saves_20sec', 0)
        max_saves_5sec = quality_data.get('max_saves_5sec', 0)
        max_saves_20sec = quality_data.get('max_saves_20sec', 0)

        # Calculate a basic quality score (lower = better quality, less suspicious clicking)
        # High spikes in short timeframes indicate potential button mashing
        if games_participated > 0:
            quality_score = f"{avg_saves_5sec:.1f}"

    scorekeeper_performance_results.append({
        'human_id': human_id,
        'context': context,
        'context_value': context_value,
        'games_participated': games_participated,
        'games_participated_rank': format_rank_percentile(games_participated_rank, total_in_rank),
        'sog_given': sog_given,
        'sog_given_rank': format_rank_percentile(sog_given_rank, total_in_rank),
        'sog_per_game': f"{sog_per_game:.2f}",
        'sog_per_game_rank': format_rank_percentile(sog_per_game_rank, total_in_rank),
        'avg_saves_5sec': f"{avg_saves_5sec:.1f}",
        'avg_saves_20sec': f"{avg_saves_20sec:.1f}",
        'max_saves_5sec': max_saves_5sec,
        'max_saves_20sec': max_saves_20sec,
        'quality_score': quality_score,
        'first_game': format_date_link(first_game.date, first_game_id) if first_game else None,
        'last_game': format_date_link(last_game.date, last_game_id) if last_game else None
    })

def get_scorekeeper_quality_data(human_id):
    """Get quality metrics for a scorekeeper from ScorekeeperSaveQuality table"""
    try:
        quality_records = db.session.query(ScorekeeperSaveQuality).filter(
            ScorekeeperSaveQuality.scorekeeper_id == human_id
        ).all()

        if not quality_records:
            return None

        total_games = len(quality_records)
        total_saves_5sec = sum(record.max_saves_per_5sec for record in quality_records)
        total_saves_20sec = sum(record.max_saves_per_20sec for record in quality_records)
        max_saves_5sec = max(record.max_saves_per_5sec for record in quality_records)
        max_saves_20sec = max(record.max_saves_per_20sec for record in quality_records)

        return {
            'avg_saves_5sec': total_saves_5sec / total_games if total_games > 0 else 0,
            'avg_saves_20sec': total_saves_20sec / total_games if total_games > 0 else 0,
            'max_saves_5sec': max_saves_5sec,
            'max_saves_20sec': max_saves_20sec,
            'total_games_with_quality_data': total_games
        }
    except Exception as e:
        # Table might not exist in sample database - return None gracefully
        return None

@scorekeeper_performance_bp.route('/', methods=['GET'])
def scorekeeper_performance():
    human_id = request.args.get('human_id')
    human_name = "All Scorekeepers"
    if human_id:
        human = db.session.query(Human).filter(Human.id == human_id).first()
        if human:
            human_name = f"Scorekeeper {human.first_name} {human.middle_name} {human.last_name}".strip()
        organizations = db.session.query(Organization).join(OrgStatsScorekeeper, Organization.id == OrgStatsScorekeeper.org_id).filter(OrgStatsScorekeeper.human_id == human_id).all()
    else:
        organizations = db.session.query(Organization).all()

    top_n = request.args.get('top_n', default=50, type=int)
    org_id = request.args.get('org_id', type=int)
    if org_id is None and organizations:
        org_id = min(org.id for org in organizations)
    level_id = request.args.get('level_id')
    season_id = request.args.get('season_id')
    return render_template('scorekeeper_performance.html', organizations=organizations, top_n=top_n, org_id=org_id, level_id=level_id, season_id=season_id, human_id=human_id, human_name=human_name)

@scorekeeper_performance_bp.route('/filter_scorekeeper_performance', methods=['POST'])
def filter_scorekeeper_performance():
    org_id = request.json.get('org_id')
    level_id = request.json.get('level_id')
    season_id = request.json.get('season_id')
    team_id = request.json.get('team_id')
    top_n = request.json.get('top_n', 50)
    human_id = request.json.get('human_id')
    min_games = request.json.get('min_games', 1)

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
        top_n = int(top_n)
    except (ValueError, TypeError):
        top_n = 50

    try:
        human_id = int(human_id)
    except (ValueError, TypeError):
        human_id = None

    try:
        min_games = int(min_games)
    except (ValueError, TypeError):
        min_games = 1

    scorekeeper_performance_results = []
    all_scorekeepers_results = []
    level_name = ""
    season_name = ""
    org_name = ""

    if org_id == ALL_ORGS_ID:
        if human_id:
            # Existing logic for ALL_ORGS_ID with human_id
            query = db.session.query(OrgStatsScorekeeper).filter(
                OrgStatsScorekeeper.human_id == human_id
            )

            # Remove the limit here, we'll apply it after sorting
            org_stats = query.order_by(OrgStatsScorekeeper.org_id).all()

            for stats in org_stats:
                organization = db.session.query(Organization).filter(Organization.id == stats.org_id).first()
                context = organization.organization_name
                quality_data = get_scorekeeper_quality_data(stats.human_id)
                append_scorekeeper_performance_result(scorekeeper_performance_results, stats, context, quality_data=quality_data)

            # Apply sorting, then min_games filter, then limit
            scorekeeper_performance_results.sort(key=lambda x: (x['games_participated']), reverse=True)
            scorekeeper_performance_results = [r for r in scorekeeper_performance_results if r['games_participated'] >= min_games]
            scorekeeper_performance_results = scorekeeper_performance_results[:top_n]
    else:
        # Get organization name
        organization = db.session.query(Organization).filter(Organization.id == org_id).first()
        org_name = organization.organization_name if organization else "Selected Organization"

        if level_id is None:
            # Show all scorekeepers at the organization level when only org_id is provided
            query = db.session.query(OrgStatsScorekeeper).filter(
                OrgStatsScorekeeper.org_id == org_id,
                OrgStatsScorekeeper.games_participated >= min_games
            )

            if human_id:
                query = query.filter(OrgStatsScorekeeper.human_id == human_id)

            # Remove limit from the query, get all results first
            org_stats = query.order_by(OrgStatsScorekeeper.sog_per_game_rank).all()

            for stats in org_stats:
                human = db.session.query(Human).filter(Human.id == stats.human_id).first()
                if human:
                    link_text = f"{human.first_name} {human.middle_name} {human.last_name}".strip()
                    link = f'<a href="{url_for("human_stats.human_stats", human_id=human.id, top_n=20)}">{link_text}</a>'
                    quality_data = get_scorekeeper_quality_data(stats.human_id)
                    append_scorekeeper_performance_result(all_scorekeepers_results, stats, link, quality_data=quality_data)

                    if human_id and human_id == stats.human_id:
                        append_scorekeeper_performance_result(scorekeeper_performance_results, stats, org_name, quality_data=quality_data)

            # Apply proper sorting, then limit the results
            all_scorekeepers_results.sort(key=lambda x: (x['games_participated']), reverse=True)
            all_scorekeepers_results = all_scorekeepers_results[:top_n]
        else:
            # Level-specific requests now fall back to organization-level stats
            # since scorekeeper quality is independent of game level/division
            level = db.session.query(Level).filter(Level.id == level_id).first()
            level_name = level.level_name if level else ""

            if season_id:
                season = db.session.query(Season).filter(Season.id == season_id).first()
                season_name = season.season_name if season else ""

            # Use org-level scorekeeper stats (scorekeeper quality is org-wide)
            query = db.session.query(OrgStatsScorekeeper).filter(
                OrgStatsScorekeeper.org_id == org_id,
                OrgStatsScorekeeper.games_participated >= min_games
            )

            if human_id:
                query = query.filter(OrgStatsScorekeeper.human_id == human_id)

            org_stats = query.order_by(OrgStatsScorekeeper.sog_per_game_rank).all()

            for stats in org_stats:
                human = db.session.query(Human).filter(Human.id == stats.human_id).first()
                if human:
                    link_text = f"{human.first_name} {human.middle_name} {human.last_name}".strip()
                    link = f'<a href="{url_for("human_stats.human_stats", human_id=human.id, top_n=20)}">{link_text}</a>'
                    quality_data = get_scorekeeper_quality_data(stats.human_id)
                    append_scorekeeper_performance_result(all_scorekeepers_results, stats, link, quality_data=quality_data)

                    if human_id and human_id == stats.human_id:
                        context = f"{org_name} (org-wide)"
                        if level_name:
                            context += f" - {level_name} level requested"
                        if season_name:
                            context += f" - {season_name}"
                        append_scorekeeper_performance_result(scorekeeper_performance_results, stats, context, quality_data=quality_data)

            # Apply proper sorting, then limit the results
            all_scorekeepers_results.sort(key=lambda x: (x['games_participated']), reverse=True)
            all_scorekeepers_results = all_scorekeepers_results[:top_n]

    # Sort the final results before returning
    all_scorekeepers_results.sort(key=lambda x: (x['games_participated']), reverse=True)
    all_scorekeepers_results = all_scorekeepers_results[:top_n]

    return jsonify({
        'scorekeeper_performance': scorekeeper_performance_results,
        'all_scorekeepers': all_scorekeepers_results,
        'level_name': level_name,
        'season_name': season_name,
        'org_name': org_name
    })

@scorekeeper_performance_bp.route('/filter_levels', methods=['POST'])
def filter_levels_route():
    org_id = request.json.get('org_id')
    human_id = request.json.get('human_id')
    return filter_levels(org_id, human_id)

@scorekeeper_performance_bp.route('/filter_seasons', methods=['POST'])
def filter_seasons_route():
    org_id = request.json.get('org_id')
    level_id = request.json.get('level_id')
    human_id = request.json.get('human_id')
    return filter_seasons(org_id, level_id, human_id)

@scorekeeper_performance_bp.route('/filter_teams', methods=['POST'])
def filter_teams_route():
    org_id = request.json.get('org_id')
    level_id = request.json.get('level_id')
    season_id = request.json.get('season_id')
    human_id = request.json.get('human_id')
    return filter_teams(org_id, level_id, season_id, human_id)