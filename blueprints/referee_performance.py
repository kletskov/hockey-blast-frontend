import logging
from flask import Blueprint, render_template, request, jsonify, url_for
from hockey_blast_common_lib.models import db, Organization, Level, Division, Season, Team, Human, Game
from hockey_blast_common_lib.stats_models import OrgStatsReferee, LevelStatsReferee, DivisionStatsReferee
from hockey_blast_common_lib.stats_utils import ALL_ORGS_ID
from .referee_performance_dropdowns import filter_levels, filter_seasons, filter_teams, get_levels_for_referee_in_org, get_divisions_and_seasons
import re
from datetime import datetime
import json

referee_performance_bp = Blueprint('referee_performance', __name__)

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

def append_referee_performance_result(referee_performance_results, stats, context, context_value=0):
    if isinstance(stats, dict):
        human_id = stats.get('human_id')
        first_game_id = stats.get('first_game_id')
        last_game_id = stats.get('last_game_id')
        games_participated = stats.get('games_participated')
        games_participated_rank = stats.get('games_participated_rank')
        penalties_given = stats.get('penalties_given')
        penalties_given_rank = stats.get('penalties_given_rank')
        penalties_per_game = stats.get('penalties_per_game')
        penalties_per_game_rank = stats.get('penalties_per_game_rank')
        gm_given = stats.get('gm_given')
        gm_given_rank = stats.get('gm_given_rank')
        gm_per_game = stats.get('gm_per_game')
        gm_per_game_rank = stats.get('gm_per_game_rank')
        total_in_rank = stats.get('total_in_rank', 1)
    else:
        human_id = stats.human_id
        first_game_id = stats.first_game_id
        last_game_id = stats.last_game_id
        games_participated = stats.games_participated
        games_participated_rank = stats.games_participated_rank
        penalties_given = stats.penalties_given
        penalties_given_rank = stats.penalties_given_rank
        penalties_per_game = stats.penalties_per_game
        penalties_per_game_rank = stats.penalties_per_game_rank
        gm_given = stats.gm_given
        gm_given_rank = stats.gm_given_rank
        gm_per_game = stats.gm_per_game
        gm_per_game_rank = stats.gm_per_game_rank
        total_in_rank = stats.total_in_rank

    first_game = db.session.query(Game.date).filter(Game.id == first_game_id).first() if first_game_id else None
    last_game = db.session.query(Game.date).filter(Game.id == last_game_id).first() if last_game_id else None
    referee_performance_results.append({
        'human_id': human_id,
        'context': context,
        'context_value': context_value,
        'games_participated': games_participated,
        'games_participated_rank': format_rank_percentile(games_participated_rank, total_in_rank),
        'penalties_given': penalties_given,
        'penalties_given_rank': format_rank_percentile(penalties_given_rank, total_in_rank),
        'penalties_per_game': f"{penalties_per_game:.2f}",
        'penalties_per_game_rank': format_rank_percentile(penalties_per_game_rank, total_in_rank),
        'gm_given': gm_given,
        'gm_given_rank': format_rank_percentile(gm_given_rank, total_in_rank),
        'gm_per_game': f"{gm_per_game:.2f}",
        'gm_per_game_rank': format_rank_percentile(gm_per_game_rank, total_in_rank),
        'first_game': format_date_link(first_game.date, first_game_id) if first_game else None,
        'last_game': format_date_link(last_game.date, last_game_id) if last_game else None
    })

@referee_performance_bp.route('/', methods=['GET'])
def referee_performance():
    human_id = request.args.get('human_id')
    human_name = "All Referees"
    if human_id:
        human = db.session.query(Human).filter(Human.id == human_id).first()
        if human:
            human_name = f"Referee {human.first_name} {human.middle_name} {human.last_name}".strip()
        organizations = db.session.query(Organization).join(OrgStatsReferee, Organization.id == OrgStatsReferee.org_id).filter(OrgStatsReferee.human_id == human_id).all()
    else:
        organizations = db.session.query(Organization).all()

    top_n = request.args.get('top_n', default=50, type=int)
    org_id = request.args.get('org_id', type=int)
    if org_id is None and organizations:
        org_id = min(org.id for org in organizations)
    level_id = request.args.get('level_id')
    season_id = request.args.get('season_id')
    return render_template('referee_performance.html', organizations=organizations, top_n=top_n, org_id=org_id, level_id=level_id, season_id=season_id, human_id=human_id, human_name=human_name)

@referee_performance_bp.route('/filter_referee_performance', methods=['POST'])
def filter_referee_performance():
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

    referee_performance_results = []
    all_referees_results = []
    level_name = ""
    season_name = ""
    org_name = ""

    if org_id == ALL_ORGS_ID:
        if human_id:
            # Existing logic for ALL_ORGS_ID with human_id
            query = db.session.query(OrgStatsReferee).filter(
                OrgStatsReferee.human_id == human_id
            )

            # Remove the limit here, we'll apply it after sorting
            org_stats = query.order_by(OrgStatsReferee.org_id).all()

            for stats in org_stats:
                organization = db.session.query(Organization).filter(Organization.id == stats.org_id).first()
                context = organization.organization_name
                append_referee_performance_result(referee_performance_results, stats, context)
            
            # Apply sorting, then min_games filter, then limit
            referee_performance_results.sort(key=lambda x: (x['games_participated']), reverse=True)
            referee_performance_results = [r for r in referee_performance_results if r['games_participated'] >= min_games]
            referee_performance_results = referee_performance_results[:top_n]
    else:
        # Get organization name
        organization = db.session.query(Organization).filter(Organization.id == org_id).first()
        org_name = organization.organization_name if organization else "Selected Organization"
        
        if level_id is None:
            # Show all referees at the organization level when only org_id is provided
            query = db.session.query(OrgStatsReferee).filter(
                OrgStatsReferee.org_id == org_id,
                OrgStatsReferee.games_participated >= min_games
            )

            if human_id:
                query = query.filter(OrgStatsReferee.human_id == human_id)

            # Remove limit from the query, get all results first
            org_stats = query.order_by(OrgStatsReferee.penalties_per_game_rank).all()

            for stats in org_stats:
                human = db.session.query(Human).filter(Human.id == stats.human_id).first()
                if human:
                    link_text = f"{human.first_name} {human.middle_name} {human.last_name}".strip()
                    link = f'<a href="{url_for("human_stats.human_stats", human_id=human.id, top_n=20)}">{link_text}</a>'
                    append_referee_performance_result(all_referees_results, stats, link)
                    
                    if human_id and human_id == stats.human_id:
                        append_referee_performance_result(referee_performance_results, stats, org_name)
            
            # Apply proper sorting, then limit the results
            all_referees_results.sort(key=lambda x: (x['games_participated']), reverse=True)
            all_referees_results = all_referees_results[:top_n]
        elif season_id is None:
            # Show referees at the level when org_id and level_id are provided
            level = db.session.query(Level).filter(Level.id == level_id).first()
            level_name = level.level_name if level else ""

            query = db.session.query(LevelStatsReferee).filter(
                LevelStatsReferee.level_id == level_id,
                LevelStatsReferee.games_participated >= min_games
            )

            if human_id:
                query = query.filter(LevelStatsReferee.human_id == human_id)
                
                # Add to referee_performance_results for specific human
                level_stats = query.order_by(LevelStatsReferee.penalties_per_game_rank).all()
                for stats in level_stats:
                    context = f"{org_name} - {level_name}"
                    append_referee_performance_result(referee_performance_results, stats, context)

            # Get all referees for this level for all_referees_results - no limit here
            level_stats = db.session.query(LevelStatsReferee).filter(
                LevelStatsReferee.level_id == level_id,
                LevelStatsReferee.games_participated >= min_games
            ).order_by(LevelStatsReferee.penalties_per_game_rank).all()

            for stats in level_stats:
                human = db.session.query(Human).filter(Human.id == stats.human_id).first()
                if human:
                    link_text = f"{human.first_name} {human.middle_name} {human.last_name}".strip()
                    link = f'<a href="{url_for("human_stats.human_stats", human_id=human.id, top_n=20)}">{link_text}</a>'
                    append_referee_performance_result(all_referees_results, stats, link)

            # Apply proper sorting, then limit the results
            all_referees_results.sort(key=lambda x: (x['games_participated']), reverse=True)
            all_referees_results = all_referees_results[:top_n]
        else:
            # Existing logic for when org_id, level_id, and season_id are all provided
            division = db.session.query(Division.id).filter(
                Division.org_id == org_id,
                Division.season_id == season_id,
                Division.level_id == level_id
            ).first()

            if division:
                division_id = division.id

                # Fetch level and season names
                level = db.session.query(Level).filter(Level.id == level_id).first()
                season = db.session.query(Season).filter(Season.id == season_id).first()
                level_name = level.level_name if level else ""
                season_name = season.season_name if season else ""

                # For human_id, add specific performance data
                if human_id:
                    human_stats = db.session.query(DivisionStatsReferee).filter(
                        DivisionStatsReferee.division_id == division_id,
                        DivisionStatsReferee.human_id == human_id
                    ).first()

                    if human_stats:
                        context = f"{org_name} - {level_name} - {season_name}"
                        append_referee_performance_result(referee_performance_results, human_stats, context)

                # Fetch all referees for the selected division and season
                all_referees_stats = db.session.query(DivisionStatsReferee).filter(
                    DivisionStatsReferee.division_id == division_id,
                    DivisionStatsReferee.games_participated >= min_games
                ).order_by(DivisionStatsReferee.penalties_per_game_rank).all()

                for stats in all_referees_stats:
                    player = db.session.query(Human).filter(Human.id == stats.human_id).first()
                    if player:
                        link_text = f"{player.first_name} {player.middle_name} {player.last_name}".strip()
                        link = f'<a href="{url_for("human_stats.human_stats", human_id=player.id, top_n=20)}">{link_text}</a>'
                        append_referee_performance_result(all_referees_results, stats, link)

    # Sort the final results before returning
    all_referees_results.sort(key=lambda x: (x['games_participated']), reverse=True)
    all_referees_results = all_referees_results[:top_n]

    return jsonify({
        'referee_performance': referee_performance_results,
        'all_referees': all_referees_results,
        'level_name': level_name,
        'season_name': season_name,
        'org_name': org_name
    })

@referee_performance_bp.route('/filter_levels', methods=['POST'])
def filter_levels_route():
    org_id = request.json.get('org_id')
    human_id = request.json.get('human_id')
    return filter_levels(org_id, human_id)

@referee_performance_bp.route('/filter_seasons', methods=['POST'])
def filter_seasons_route():
    org_id = request.json.get('org_id')
    level_id = request.json.get('level_id')
    human_id = request.json.get('human_id')
    return filter_seasons(org_id, level_id, human_id)

@referee_performance_bp.route('/filter_teams', methods=['POST'])
def filter_teams_route():
    org_id = request.json.get('org_id')
    level_id = request.json.get('level_id')
    season_id = request.json.get('season_id')
    human_id = request.json.get('human_id')
    return filter_teams(org_id, level_id, season_id, human_id)
