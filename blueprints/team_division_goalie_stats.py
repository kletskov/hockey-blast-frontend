from flask import Blueprint, request, jsonify
from hockey_blast_common_lib.models import db, Game, Goal, Penalty, GameRoster, Human
from sqlalchemy.sql import func, case
from collections import defaultdict

team_division_goalie_stats_bp = Blueprint('team_division_goalie_stats', __name__)

def compute_goalie_stats(games, team_id):
    # Initialize stats dictionary
    stats_dict = defaultdict(lambda: {
        'games_played': 0,
        'goals_allowed': 0,
        'shots_faced': 0,
        'goals_allowed_per_game': 0.0,
        'save_percentage': 0.0,
        'game_ids': [],
        'first_game_id': None,
        'last_game_id': None,
        'total_in_rank': 0
    })

    # Aggregate games played, goals allowed, and shots faced for each goalie
    goalie_stats = db.session.query(
        GameRoster.human_id,
        func.count(Game.id).label('games_played'),
        func.sum(case((GameRoster.team_id == Game.home_team_id, Game.visitor_final_score), else_=Game.home_final_score)).label('goals_allowed'),
        func.sum(case((GameRoster.team_id == Game.home_team_id, Game.visitor_period_1_shots + Game.visitor_period_2_shots + Game.visitor_period_3_shots + Game.visitor_ot_shots + Game.visitor_so_shots), else_=Game.home_period_1_shots + Game.home_period_2_shots + Game.home_period_3_shots + Game.home_ot_shots + Game.home_so_shots)).label('shots_faced'),
        func.array_agg(Game.id).label('game_ids')
    ).join(Game, GameRoster.game_id == Game.id).filter(
        Game.id.in_(games),
        GameRoster.team_id == team_id,
        GameRoster.role.ilike('g')
    ).group_by(GameRoster.human_id).all()

    # Combine the results
    for stat in goalie_stats:
        key = stat.human_id
        stats_dict[key]['games_played'] += stat.games_played
        stats_dict[key]['goals_allowed'] += stat.goals_allowed if stat.goals_allowed is not None else 0
        stats_dict[key]['shots_faced'] += stat.shots_faced if stat.shots_faced is not None else 0
        stats_dict[key]['game_ids'].extend(stat.game_ids)

    # Calculate per game stats
    for key, stat in stats_dict.items():
        if stat['games_played'] > 0:
            stat['goals_allowed_per_game'] = stat['goals_allowed'] / stat['games_played']
            stat['save_percentage'] = 1 - (stat['goals_allowed'] / stat['shots_faced']) if stat['shots_faced'] > 0 else 0.0
            stat['first_game_id'] = min(stat['game_ids'])
            stat['last_game_id'] = max(stat['game_ids'])

    total_in_rank = len(stats_dict)
    for key in stats_dict:
        stats_dict[key]['total_in_rank'] = total_in_rank

    # Assign ranks within each level
    def assign_ranks(stats_dict, field, reverse=True):
        sorted_stats = sorted(stats_dict.items(), key=lambda x: x[1][field], reverse=reverse)
        for rank, (key, stat) in enumerate(sorted_stats, start=1):
            stats_dict[key][f'{field}_rank'] = rank

    assign_ranks(stats_dict, 'games_played')
    assign_ranks(stats_dict, 'goals_allowed', reverse=False)
    assign_ranks(stats_dict, 'goals_allowed_per_game', reverse=False)
    assign_ranks(stats_dict, 'shots_faced')
    assign_ranks(stats_dict, 'save_percentage')

    return stats_dict

@team_division_goalie_stats_bp.route('/team_division_goalie_stats', methods=['POST'])
def get_team_division_goalie_stats():
    data = request.get_json()
    team_id = data.get('team_id')
    games = data.get('games')

    if not team_id or not games:
        return jsonify({'error': 'team_id and games are required'}), 400

    stats = compute_goalie_stats(games, team_id)
    return jsonify(stats)
