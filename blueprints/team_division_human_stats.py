from flask import Blueprint, request, jsonify
from hockey_blast_common_lib.models import db, Game, Goal, Penalty, GameRoster, Human
from sqlalchemy.sql import func, case
from collections import defaultdict

team_division_stats_bp = Blueprint('team_division_stats', __name__)

def compute_skater_stats(games, team_id):
    # Initialize stats dictionary
    stats_dict = defaultdict(lambda: {
        'games_played': 0,
        'goals': 0,
        'assists': 0,
        'penalties': 0,
        'gm_penalties': 0,
        'points': 0,
        'goals_per_game': 0.0,
        'points_per_game': 0.0,
        'assists_per_game': 0.0,
        'penalties_per_game': 0.0,
        'gm_penalties_per_game': 0.0,
        'game_ids': [],
        'first_game_id': None,
        'last_game_id': None,
        'total_in_rank': 0
    })

    # Aggregate games played for each human in each division, excluding goalies
    games_played_stats = db.session.query(
        GameRoster.human_id,
        func.count(Game.id).label('games_played'),
        func.array_agg(Game.id).label('game_ids')
    ).join(Game, Game.id == GameRoster.game_id).filter(
        Game.id.in_(games),
        GameRoster.team_id == team_id,
        ~GameRoster.role.ilike('g')
    ).group_by(GameRoster.human_id).all()

    # Aggregate goals for each human in each division, excluding goalies
    goals_stats = db.session.query(
        Goal.goal_scorer_id.label('human_id'),
        func.count(Goal.id).label('goals'),
        func.array_agg(Goal.game_id).label('goal_game_ids')
    ).join(Game, Game.id == Goal.game_id).join(GameRoster, Game.id == GameRoster.game_id).filter(
        Game.id.in_(games),
        GameRoster.team_id == team_id,
        Goal.goal_scorer_id == GameRoster.human_id,
        ~GameRoster.role.ilike('g')
    ).group_by(Goal.goal_scorer_id).all()

    # Aggregate assists for each human in each division, excluding goalies
    assists_stats = db.session.query(
        Goal.assist_1_id.label('human_id'),
        func.count(Goal.id).label('assists'),
        func.array_agg(Goal.game_id).label('assist_game_ids')
    ).join(Game, Game.id == Goal.game_id).join(GameRoster, Game.id == GameRoster.game_id).filter(
        Game.id.in_(games),
        GameRoster.team_id == team_id,
        Goal.assist_1_id == GameRoster.human_id,
        ~GameRoster.role.ilike('g')
    ).group_by(Goal.assist_1_id).all()

    assists_stats_2 = db.session.query(
        Goal.assist_2_id.label('human_id'),
        func.count(Goal.id).label('assists'),
        func.array_agg(Goal.game_id).label('assist_2_game_ids')
    ).join(Game, Game.id == Goal.game_id).join(GameRoster, Game.id == GameRoster.game_id).filter(
        Game.id.in_(games),
        GameRoster.team_id == team_id,
        Goal.assist_2_id == GameRoster.human_id,
        ~GameRoster.role.ilike('g')
    ).group_by(Goal.assist_2_id).all()

    # Aggregate penalties for each human in each division, excluding goalies
    penalties_stats = db.session.query(
        Penalty.penalized_player_id.label('human_id'),
        func.count(Penalty.id).label('penalties'),
        func.sum(case((Penalty.penalty_minutes == 'GM', 1), else_=0)).label('gm_penalties'),
        func.array_agg(Penalty.game_id).label('penalty_game_ids')
    ).join(Game, Game.id == Penalty.game_id).join(GameRoster, Game.id == GameRoster.game_id).filter(
        Game.id.in_(games),
        GameRoster.team_id == team_id,
        Penalty.penalized_player_id == GameRoster.human_id,
        ~GameRoster.role.ilike('g')
    ).group_by(Penalty.penalized_player_id).all()

    # Combine the results
    for stat in games_played_stats:
        key = stat.human_id
        stats_dict[key]['games_played'] += stat.games_played
        stats_dict[key]['game_ids'].extend(stat.game_ids)

    for stat in goals_stats:
        key = stat.human_id
        stats_dict[key]['goals'] += stat.goals
        stats_dict[key]['points'] += stat.goals

    for stat in assists_stats:
        key = stat.human_id
        stats_dict[key]['assists'] += stat.assists
        stats_dict[key]['points'] += stat.assists

    for stat in assists_stats_2:
        key = stat.human_id
        stats_dict[key]['assists'] += stat.assists
        stats_dict[key]['points'] += stat.assists

    for stat in penalties_stats:
        key = stat.human_id
        stats_dict[key]['penalties'] += stat.penalties
        stats_dict[key]['gm_penalties'] += stat.gm_penalties

    # Calculate per game stats
    for key, stat in stats_dict.items():
        if stat['games_played'] > 0:
            stat['goals_per_game'] = stat['goals'] / stat['games_played']
            stat['points_per_game'] = stat['points'] / stat['games_played']
            stat['assists_per_game'] = stat['assists'] / stat['games_played']
            stat['penalties_per_game'] = stat['penalties'] / stat['games_played']
            stat['gm_penalties_per_game'] = stat['gm_penalties'] / stat['games_played']

    # Populate first_game_id and last_game_id
    for key, stat in stats_dict.items():
        all_game_ids = stat['game_ids']
        if all_game_ids:
            first_game = db.session.query(Game).filter(Game.id.in_(all_game_ids)).order_by(Game.date, Game.time).first()
            last_game = db.session.query(Game).filter(Game.id.in_(all_game_ids)).order_by(Game.date.desc(), Game.time.desc()).first()
            stat['first_game_id'] = first_game.id if first_game else None
            stat['last_game_id'] = last_game.id if last_game else None

    # Calculate total_in_rank
    total_in_rank = len(stats_dict)
    for key in stats_dict:
        stats_dict[key]['total_in_rank'] = total_in_rank

    # Assign ranks within each level
    def assign_ranks(stats_dict, field):
        sorted_stats = sorted(stats_dict.items(), key=lambda x: x[1][field], reverse=True)
        for rank, (key, stat) in enumerate(sorted_stats, start=1):
            stats_dict[key][f'{field}_rank'] = rank

    assign_ranks(stats_dict, 'games_played')
    assign_ranks(stats_dict, 'goals')
    assign_ranks(stats_dict, 'assists')
    assign_ranks(stats_dict, 'points')
    assign_ranks(stats_dict, 'penalties')
    assign_ranks(stats_dict, 'gm_penalties')
    assign_ranks(stats_dict, 'goals_per_game')
    assign_ranks(stats_dict, 'points_per_game')
    assign_ranks(stats_dict, 'assists_per_game')
    assign_ranks(stats_dict, 'penalties_per_game')
    assign_ranks(stats_dict, 'gm_penalties_per_game')

    return stats_dict

@team_division_stats_bp.route('/team_division_stats', methods=['POST'])
def team_division_stats():
    team_id = request.json.get('team_id')
    division_id = request.json.get('division_id')
    role = request.json.get('role', 'skater')

    # Fetch games for the given team and division
    games = db.session.query(Game.id).filter(
        Game.division_id == division_id,
        (Game.home_team_id == team_id) | (Game.visitor_team_id == team_id)
    ).all()
    games = [game.id for game in games]

    # Compute skater stats
    stats_dict = compute_skater_stats(games, team_id)

    return jsonify({
        'all_stats': stats_dict
    })
