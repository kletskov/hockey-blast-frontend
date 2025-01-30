import logging
from flask import Blueprint, request, jsonify, render_template, url_for, g
from hockey_blast_common_lib.models import db, Game, GameRoster, Division, Goal, Penalty, Shootout, Human, League, Team
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Limiter
# limiter = Limiter(
#     key_func=get_remote_address,
#     default_limits=["1 per 2 seconds", "1000 per day"]
# )

# Custom limit for specific user agent
# user_agent_limiter = Limiter(
#     key_func=lambda: request.headers.get('User-Agent'),
#     default_limits=["1 per minute"]
# )

game_card_bp = Blueprint('game_card', __name__)

# BLOCKED_USER_AGENT = "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.6834.83 Mobile Safari/537.36 (compatible; GoogleOther)"
# BLOCKED_IPS = ["66.249.72.103", "66.249.72.204"]

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

@game_card_bp.before_request
def before_request():
    g.limited = False
    user_agent = request.headers.get('User-Agent')
    client_ip = get_client_ip()
    logger.info(f"Request from {client_ip} with User-Agent {user_agent}")
    # if user_agent == BLOCKED_USER_AGENT or client_ip in BLOCKED_IPS:
    #     logger.warning(f"Blocked request from {client_ip} with User-Agent {user_agent}")
    #     return jsonify({"error": "Request blocked"}), 403

@game_card_bp.after_request
def after_request(response):
    client_ip = get_client_ip()
    if response.status_code == 429:
        g.limited = True
    logger.info(f"Request to {request.path} from {client_ip} with User-Agent {request.headers.get('User-Agent')} - Status: {response.status_code} - Limited: {g.limited}")
    return response

@game_card_bp.route('/game_card', methods=['GET'])
# @limiter.limit("1 per 2 seconds")
# @limiter.limit("1000 per day")
# @user_agent_limiter.limit("1 per minute", key_func=lambda: BLOCKED_USER_AGENT)
def game_card():
    game_id = request.args.get('game_id')
    
    if not game_id:
        return jsonify({"error": "Please provide game_id"}), 400
    
    try:
        game_id = int(game_id)  # Ensure game_id is an integer
    except ValueError:
        return jsonify({"error": f"Incorrect game_id: {game_id}"}), 404
    
    # Fetch the game data
    game = db.session.query(Game).filter(Game.id == game_id).first()
    if not game:
        return jsonify({"error": "Game not found"}), 404
    
    # Fetch related data
    division = db.session.query(Division).filter(Division.id == game.division_id).first()
    league = db.session.query(League).filter(League.id == division.league_number).first()
    scorekeeper = db.session.query(Human).filter(Human.id == game.scorekeeper_id).first()
    referee_1 = db.session.query(Human).filter(Human.id == game.referee_1_id).first()
    referee_2 = db.session.query(Human).filter(Human.id == game.referee_2_id).first()
    
    # Fetch team names
    visitor_team = db.session.query(Team).filter(Team.id == game.visitor_team_id).first()
    home_team = db.session.query(Team).filter(Team.id == game.home_team_id).first()
    
    # Fetch rosters
    home_roster = db.session.query(GameRoster, Human).join(Human, GameRoster.human_id == Human.id).filter(GameRoster.game_id == game_id, GameRoster.team_id == game.home_team_id).all()
    visitor_roster = db.session.query(GameRoster, Human).join(Human, GameRoster.human_id == Human.id).filter(GameRoster.game_id == game_id, GameRoster.team_id == game.visitor_team_id).all()
    
    # Fetch goals
    goals = db.session.query(Goal).filter(Goal.game_id == game_id).all()
    for goal in goals:
        goal.scorer_name = db.session.query(Human).filter(Human.id == goal.goal_scorer_id).first()
        goal.assist_1_name = db.session.query(Human).filter(Human.id == goal.assist_1_id).first()
        goal.assist_2_name = db.session.query(Human).filter(Human.id == goal.assist_2_id).first()
    
    # Convert time to sortable format (handling both 'MM:SS' and 'SS.SS' formats)
    for goal in goals:
        if goal.time:
            if ':' in goal.time:
                minutes, seconds = goal.time.split(':')
                minutes = int(minutes)
                seconds = float(seconds)
            else:
                minutes = 0
                seconds = float(goal.time)
            goal.sortable_time = minutes * 60 + seconds
        else:
            goal.sortable_time = 0  # Default value if time is empty

    # Sort goals by period ascending and time descending
    goals.sort(key=lambda x: (x.period, -x.sortable_time))
    
    # Determine unique periods
    unique_periods = sorted(set(goal.period for goal in goals))
    
    # Count goals per period for each team
    visitor_goals_per_period = {period: 0 for period in unique_periods}
    home_goals_per_period = {period: 0 for period in unique_periods}
    for goal in goals:
        period = str(goal.period)
        if goal.scoring_team_id == game.visitor_team_id:
            visitor_goals_per_period[period] += 1
        elif goal.scoring_team_id == game.home_team_id:
            home_goals_per_period[period] += 1
    
    # Fetch penalties
    penalties = db.session.query(Penalty).filter(Penalty.game_id == game_id).order_by(Penalty.penalty_sequence_number).all()
    for penalty in penalties:
        player = db.session.query(Human).filter(Human.id == penalty.penalized_player_id).first()
        team = db.session.query(Team).filter(Team.id == penalty.team_id).first()
        penalty.player_name = f"{player.first_name} {player.last_name}" if player else "Unknown"
        penalty.team_name = team.name if team else "Unknown"
        penalty.team_link = url_for('game_card.game_card', game_id=penalty.team_id)
    
    # Fetch shootouts
    shootouts = db.session.query(Shootout).filter(Shootout.game_id == game_id).all()
    visitor_shootouts = [s for s in shootouts if s.shooting_team_id == game.visitor_team_id]
    home_shootouts = [s for s in shootouts if s.shooting_team_id == game.home_team_id]

    # Interleave shootouts
    interleaved_shootouts = []
    for i in range(max(len(visitor_shootouts), len(home_shootouts))):
        if i < len(visitor_shootouts):
            interleaved_shootouts.append(visitor_shootouts[i])
        if i < len(home_shootouts):
            interleaved_shootouts.append(home_shootouts[i])

    for shootout in interleaved_shootouts:
        shooter = db.session.query(Human).filter(Human.id == shootout.shooter_id).first()
        goalie = db.session.query(Human).filter(Human.id == shootout.goalie_id).first()
        team = db.session.query(Team).filter(Team.id == shootout.shooting_team_id).first()
        shootout.shooter_name = f"{shooter.first_name} {shooter.last_name}" if shooter else "Unknown"
        shootout.goalie_name = f"{goalie.first_name} {goalie.last_name}" if goalie else "Unknown"
        shootout.team_name = team.name if team else "Unknown"
        shootout.team_link = url_for('game_card.game_card', game_id=shootout.shooting_team_id)
    
    # Calculate total shots
    try:
        visitor_total_shots = (
            game.visitor_period_1_shots + game.visitor_period_2_shots + game.visitor_period_3_shots + game.visitor_ot_shots
        )
    except TypeError:
        visitor_total_shots = None

    try:
        home_total_shots = (
            game.home_period_1_shots + game.home_period_2_shots + game.home_period_3_shots + game.home_ot_shots
        )
    except TypeError:
        home_total_shots = None

    return render_template('game_card.html', game=game, division=division, league=league, scorekeeper=scorekeeper, referee_1=referee_1, referee_2=referee_2, home_roster=home_roster, visitor_roster=visitor_roster, goals=goals, visitor_goals_per_period=visitor_goals_per_period, home_goals_per_period=home_goals_per_period, penalties=penalties, shootouts=interleaved_shootouts, visitor_team=visitor_team, home_team=home_team, visitor_total_shots=visitor_total_shots, home_total_shots=home_total_shots, unique_periods=unique_periods, game_number = game.game_number)