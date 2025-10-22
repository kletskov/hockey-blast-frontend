import logging
from flask import Blueprint, render_template, request, jsonify, url_for
from hockey_blast_common_lib.models import db, Human, Game
from hockey_blast_common_lib.stats_models import OrgStatsScorekeeper
from hockey_blast_common_lib.stats_utils import ALL_ORGS_ID
from datetime import datetime
from sqlalchemy import desc

scorekeeper_quality_bp = Blueprint('scorekeeper_quality', __name__)

def format_rank_percentile(rank, total, reverse=False):
    """Format rank and percentile for display"""
    if not total or total == 0:
        return f"{rank or 0}/{total or 0}<br>N/A"

    if reverse:
        # For "bad" stats like excessive save usage - higher rank = worse performance
        percentile = (rank / total) * 100
    else:
        # For "good" stats - lower rank = better performance
        percentile = (total - rank) / total * 100

    return f"{rank}/{total}<br>{percentile:.0f}th"

def format_date_link(date, game_id):
    """Format date as clickable link to game card"""
    if date:
        date_parts = date.strftime('%m/%d/%y').split('/')
        formatted_date = f"{date_parts[0]}<br>{date_parts[1]}<br>{date_parts[2]}"
        return f"<a href='{url_for('game_card.game_card', game_id=game_id)}'>{formatted_date}</a>"
    return None


def get_scorekeepers_with_quality_issues(min_games=10, limit=50):
    """Get scorekeepers ranked by potential quality issues using aggregated cross-organizational stats"""

    # Query OrgStatsScorekeeper for ALL_ORGS_ID quality data only
    query = db.session.query(OrgStatsScorekeeper).filter(
        OrgStatsScorekeeper.org_id == ALL_ORGS_ID,
        OrgStatsScorekeeper.quality_score.isnot(None),
        OrgStatsScorekeeper.games_participated >= min_games
    )

    # Order by quality score descending (worst quality first)
    results = query.order_by(desc(OrgStatsScorekeeper.quality_score)).limit(limit).all()

    # Get total count for rankings
    total_count_query = db.session.query(OrgStatsScorekeeper).filter(
        OrgStatsScorekeeper.org_id == ALL_ORGS_ID,
        OrgStatsScorekeeper.quality_score.isnot(None),
        OrgStatsScorekeeper.games_participated >= min_games
    )

    total_count = total_count_query.count()

    # Format results
    scorekeeper_data = []
    for idx, stats in enumerate(results):
        human = db.session.query(Human).filter(Human.id == stats.human_id).first()
        if not human:
            continue

        scorekeeper_data.append({
            'human_id': stats.human_id,
            'human_name': f"{human.first_name} {human.middle_name or ''} {human.last_name}".strip(),
            'total_games_recorded': stats.games_participated,
            'avg_max_saves_5sec': stats.avg_max_saves_per_5sec or 0,
            'avg_max_saves_20sec': stats.avg_max_saves_per_20sec or 0,
            'peak_saves_5sec': stats.peak_max_saves_per_5sec or 0,
            'peak_saves_20sec': stats.peak_max_saves_per_20sec or 0,
            'quality_score': stats.quality_score or 0,
            'quality_rank': idx + 1,
            'total_in_rank': total_count,
            'first_game_id': stats.first_game_id,
            'last_game_id': stats.last_game_id,
            'avg_saves_per_game': stats.avg_saves_per_game or 0.0,
            'org_id': stats.org_id
        })

    return scorekeeper_data

@scorekeeper_quality_bp.route('/', methods=['GET'])
def scorekeeper_quality():
    """Main scorekeeper quality page - cross-organizational analysis"""
    top_n = request.args.get('top_n', default=50, type=int)
    min_games = request.args.get('min_games', default=10, type=int)

    return render_template('scorekeeper_quality.html',
                         top_n=top_n,
                         min_games=min_games)

@scorekeeper_quality_bp.route('/filter_scorekeeper_quality', methods=['POST'])
def filter_scorekeeper_quality():
    """API endpoint to filter scorekeeper quality data - cross-organizational only"""
    top_n = request.json.get('top_n', 50)
    min_games = request.json.get('min_games', 10)

    # Convert parameters
    try:
        top_n = int(top_n)
    except (ValueError, TypeError):
        top_n = 50

    try:
        min_games = int(min_games)
    except (ValueError, TypeError):
        min_games = 10

    # Always show all organizations
    org_name = "All Organizations"

    # Get scorekeeper quality data (always cross-organizational)
    scorekeepers_data = get_scorekeepers_with_quality_issues(
        min_games=min_games,
        limit=top_n
    )

    # Format results for frontend
    results = []
    for scorekeeper in scorekeepers_data:
        # Get first and last game dates
        first_game = None
        last_game = None
        if scorekeeper['first_game_id']:
            first_game = db.session.query(Game.date).filter(Game.id == scorekeeper['first_game_id']).first()
        if scorekeeper['last_game_id']:
            last_game = db.session.query(Game.date).filter(Game.id == scorekeeper['last_game_id']).first()

        # Create scorekeeper link
        link_text = scorekeeper['human_name']
        scorekeeper_link = f'<a href="{url_for("human_stats.human_stats", human_id=scorekeeper["human_id"], top_n=20)}">{link_text}</a>'

        results.append({
            'scorekeeper': scorekeeper_link,
            'quality_rank': format_rank_percentile(scorekeeper['quality_rank'], scorekeeper['total_in_rank'], reverse=True),
            'quality_score': f"{scorekeeper['quality_score']:.1f}",
            'games_recorded': scorekeeper['total_games_recorded'],
            'avg_max_5sec': f"{scorekeeper['avg_max_saves_5sec']:.1f}",
            'avg_max_20sec': f"{scorekeeper['avg_max_saves_20sec']:.1f}",
            'peak_5sec': scorekeeper['peak_saves_5sec'],
            'peak_20sec': scorekeeper['peak_saves_20sec'],
            'avg_saves_per_game': f"{scorekeeper['avg_saves_per_game']:.1f}",
            'first_game': format_date_link(first_game.date, scorekeeper['first_game_id']) if first_game else None,
            'last_game': format_date_link(last_game.date, scorekeeper['last_game_id']) if last_game else None
        })

    return jsonify({
        'scorekeepers': results,
        'org_name': org_name,
        'total_found': len(results)
    })

