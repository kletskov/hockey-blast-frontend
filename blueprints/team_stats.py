from flask import Blueprint, request, jsonify, render_template, url_for
from hockey_blast_common_lib.models import db, Team, Goal, Game, GameRoster, Human, Division
from datetime import datetime

team_stats_bp = Blueprint('team_stats', __name__)

@team_stats_bp.route('/team_stats', methods=['GET'])
def team_stats():
    team_id = request.args.get('team_id')
    top_n = request.args.get('top_n', default=50, type=int)
    
    if not team_id:
        return jsonify({"error": "Please provide team_id"}), 400
    
    team_id = int(team_id)  # Ensure team_id is an integer
    
    team = db.session.query(Team).filter(Team.id == team_id).first()
    
    if not team:
        return jsonify({"error": "Team not found"}), 404
    
    team_name = team.name

    # Query games where the team was present
    games = db.session.query(Game).filter(
        (Game.home_team_id == team_id) | (Game.visitor_team_id == team_id)
    ).all()
    
    # Combine date and time into a unified datetime object
    for game in games:
        game.game_datetime = datetime.combine(game.date, game.time)
    
    # Sort games by the unified datetime object in descending order
    games.sort(key=lambda game: game.game_datetime, reverse=True)
    
    # Filter completed games
    completed_games = [game for game in games if game.status.startswith('Final')]
    
    # Get the latest game and its division ID
    latest_game = games[0] if games else None
    division_id = latest_game.division_id if latest_game else None
    
    last_division_name = db.session.query(Division).filter(Division.id == division_id).first().level if division_id else None

    # Day of week mapping
    day_of_week_map = {1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat', 7: 'Sun'}
    
    # Extract recent and upcoming games data from games with the same division ID
    recent_and_upcoming_games_data = []
    for game in games:
        if game.division_id != division_id:
            continue
        visitor_team = db.session.query(Team).filter(Team.id == game.visitor_team_id).first()
        home_team = db.session.query(Team).filter(Team.id == game.home_team_id).first()
        day_of_week = day_of_week_map.get(game.day_of_week, '')
        date_time = f"{day_of_week} {game.date.strftime('%m/%d/%y')} {game.time.strftime('%I:%M%p')}"
        if game.status.startswith('Final'):
            if game.home_team_id == team_id:
                if game.home_final_score > game.visitor_final_score:
                    color = "#7CFC00"
                elif game.home_final_score < game.visitor_final_score:
                    color = "red"
                else:
                    color = "black"
                final_score = f"<span style='color:black;'>{game.visitor_final_score}</span> : <strong style='color:{color};'>{game.home_final_score}</strong>"
            elif game.visitor_team_id == team_id:
                if game.visitor_final_score > game.home_final_score:
                    color = "#7CFC00"
                elif game.visitor_final_score < game.home_final_score:
                    color = "red"
                else:
                    color = "black"
                final_score = f"<strong style='color:{color};'>{game.visitor_final_score}</strong> : <span style='color:black;'>{game.home_final_score}</span>"
            else:
                final_score = f"<span style='color:black;'>{game.visitor_final_score}</span> : <span style='color:black;'>{game.home_final_score}</span>"
        else:
            final_score = "TBD"
        recent_and_upcoming_games_data.append({
            'date_time': f"<a href='{url_for('game_card.game_card', game_id=game.id)}'>{date_time}</a>",
            'team_names': f"<a href='{url_for('team_stats.team_stats', team_id=visitor_team.id)}'>{visitor_team.name}</a> at <a href='{url_for('team_stats.team_stats', team_id=home_team.id)}'>{home_team.name}</a>",
            'final_score': f"<a href='{url_for('game_card.game_card', game_id=game.id)}'>{final_score}</a>"
        })

    # Existing logic
    goals_scored = db.session.query(Goal).filter(Goal.scoring_team_id == team_id).count()
    goals_against = db.session.query(Goal).filter(Goal.opposing_team_id == team_id).count()
    total_goals = goals_scored + goals_against
    goals_scored_percentage = (goals_scored / total_goals * 100) if total_goals > 0 else 0
    goals_against_percentage = (goals_against / total_goals * 100) if total_goals > 0 else 0
    
    if completed_games:
        first_game = min(completed_games, key=lambda game: game.date)
        last_game = max(completed_games, key=lambda game: game.date)
        first_game_date = first_game.date.strftime('%m/%d/%Y')
        first_game_id = first_game.id
        last_game_date = last_game.date.strftime('%m/%d/%Y')
        last_game_id = last_game.id
    else:
        first_game_date = "Never"
        first_game_id = -1
        last_game_date = "Never"
        last_game_id = -1

    total_games_played = len(completed_games)
    
    total_wins = 0
    total_losses = 0
    for game in completed_games:
        if game.home_team_id == team_id and game.home_final_score > game.visitor_final_score:
            total_wins += 1
        elif game.visitor_team_id == team_id and game.visitor_final_score > game.home_final_score:
            total_wins += 1
        elif game.home_team_id == team_id and game.home_final_score < game.visitor_final_score:
            total_losses += 1
        elif game.visitor_team_id == team_id and game.visitor_final_score < game.home_final_score:
            total_losses += 1
    
    win_percentage = (total_wins / total_games_played * 100) if total_games_played > 0 else 0
    loss_percentage = (total_losses / total_games_played * 100) if total_games_played > 0 else 0
    
    playoff_and_championship_games = [game for game in completed_games if game.game_type in ['Playoff', 'Championship']]
    playoff_games_played = len(playoff_and_championship_games)
    
    playoff_wins = 0
    playoff_losses = 0
    for game in playoff_and_championship_games:
        if game.home_team_id == team_id and game.home_final_score > game.visitor_final_score:
            playoff_wins += 1
        elif game.visitor_team_id == team_id and game.visitor_final_score > game.home_final_score:
            playoff_wins += 1
        elif game.home_team_id == team_id and game.home_final_score < game.visitor_final_score:
            playoff_losses += 1
        elif game.visitor_team_id == team_id and game.visitor_final_score < game.home_final_score:
            playoff_losses += 1
    
    playoff_win_percentage = (playoff_wins / playoff_games_played * 100) if playoff_games_played > 0 else 0
    playoff_loss_percentage = (playoff_losses / playoff_games_played * 100) if playoff_games_played > 0 else 0
    
    championship_games = [game for game in completed_games if game.game_type == 'Championship']
    championship_games_played = len(championship_games)
    
    championship_wins = 0
    championship_losses = 0
    for game in championship_games:
        if game.home_team_id == team_id and game.home_final_score > game.visitor_final_score:
            championship_wins += 1
        elif game.visitor_team_id == team_id and game.visitor_final_score > game.home_final_score:
            championship_wins += 1
        elif game.home_team_id == team_id and game.home_final_score < game.visitor_final_score:
            championship_losses += 1
        elif game.visitor_team_id == team_id and game.visitor_final_score < game.home_final_score:
            championship_losses += 1
    
    championship_win_percentage = (championship_wins / championship_games_played * 100) if championship_games_played > 0 else 0
    championship_loss_percentage = (championship_losses / championship_games_played * 100) if championship_games_played > 0 else 0
    
    # Extract championship years and corresponding game links for championships won
    championship_wins_data = []
    for game in championship_games:
        if (game.home_team_id == team_id and game.home_final_score > game.visitor_final_score) or \
           (game.visitor_team_id == team_id and game.visitor_final_score > game.home_final_score):
            division = db.session.query(Division).filter(Division.id == game.division_id).first()
            level = division.level if division else "Unknown Level"
            championship_wins_data.append({
                'year': game.date.year,
                'level': level,
                'game_id': game.id
            })

    # Sort championship wins data by year in increasing order
    championship_wins_data.sort(key=lambda x: x['year'])

    playoff_and_championship_goals_scored = db.session.query(Goal).join(Game).filter(
        Goal.scoring_team_id == team_id,
        Game.game_type.in_(['Playoff', 'Championship']),
        Game.home_final_score.isnot(None),
        Game.visitor_final_score.isnot(None),
        Game.home_final_score >= 0,
        Game.visitor_final_score >= 0
    ).count()
    
    playoff_and_championship_goals_against = db.session.query(Goal).join(Game).filter(
        Goal.opposing_team_id == team_id,
        Game.game_type.in_(['Playoff', 'Championship']),
        Game.home_final_score.isnot(None),
        Game.visitor_final_score.isnot(None),
        Game.home_final_score >= 0,
        Game.visitor_final_score >= 0
    ).count()
    
    total_playoff_goals = playoff_and_championship_goals_scored + playoff_and_championship_goals_against
    playoff_goals_scored_percentage = (playoff_and_championship_goals_scored / total_playoff_goals * 100) if total_playoff_goals > 0 else 0
    playoff_goals_against_percentage = (playoff_and_championship_goals_against / total_playoff_goals * 100) if total_playoff_goals > 0 else 0
    
    goals_by_team = db.session.query(
        Goal.opposing_team_id.label('opponent_team_id'),
        db.func.count(Goal.id).label('goals_scored')
    ).filter(
        Goal.scoring_team_id == team_id
    ).group_by(
        Goal.opposing_team_id
    ).all()
    
    goals_against_team = db.session.query(
        Goal.scoring_team_id.label('opponent_team_id'),
        db.func.count(Goal.id).label('goals_against')
    ).filter(
        Goal.opposing_team_id == team_id
    ).group_by(
        Goal.scoring_team_id
    ).all()
    
    performance_stats = {}
    
    for g in goals_by_team:
        if g.opponent_team_id not in performance_stats:
            performance_stats[g.opponent_team_id] = {'goals_scored': 0, 'goals_against': 0}
        performance_stats[g.opponent_team_id]['goals_scored'] = g.goals_scored
    
    for g in goals_against_team:
        if g.opponent_team_id not in performance_stats:
            performance_stats[g.opponent_team_id] = {'goals_scored': 0, 'goals_against': 0}
        performance_stats[g.opponent_team_id]['goals_against'] = g.goals_against
    
    performance_stats_list = []
    for opponent_team_id, stats in performance_stats.items():
        if opponent_team_id == team_id:
            continue
        opponent_team = db.session.query(Team).filter(Team.id == opponent_team_id).first()
        if opponent_team:
            performance_stats_list.append({
                'opponent_team_name': opponent_team.name,
                'opponent_team_id': opponent_team.id,
                'goal_diff': stats['goals_scored'] - stats['goals_against'],
                'goals_scored': stats['goals_scored'],
                'goals_against': stats['goals_against']
            })
    
    performance_stats_list.sort(key=lambda x: x['goal_diff'], reverse=True)
    
    best_performance = performance_stats_list[:top_n]
    worst_performance = performance_stats_list[-top_n:][::-1]
    
    human_game_counts = db.session.query(
        GameRoster.human_id,
        db.func.count(GameRoster.game_id).label('games_played'),
        db.func.array_agg(GameRoster.role).label('roles')
    ).filter(
        GameRoster.team_id == team_id
    ).group_by(
        GameRoster.human_id
    ).order_by(
        db.func.count(GameRoster.game_id).desc()
    ).limit(top_n).all()
    
    long_timers = []
    for human_id, games_played, roles in human_game_counts:
        human = db.session.query(Human).filter(Human.id == human_id).first()
        full_name = f"{human.first_name} {human.middle_name} {human.last_name}".strip()
        roles_str = ','.join(set(role for role in roles if role))
        long_timers.append({
            'human_id': human_id,
            'human_name': full_name,
            'roles': roles_str,
            'games_played': games_played
        })
    
    return render_template(
        'team_stats.html',
        team=team,  # Pass the team object to the template
        team_name=team_name,
        team_id=team_id,
        goals_scored=goals_scored,
        goals_against=goals_against,
        goals_scored_percentage=goals_scored_percentage,
        goals_against_percentage=goals_against_percentage,
        first_game_date=first_game_date,
        last_game_date=last_game_date,
        first_game_id=first_game_id,
        last_game_id=last_game_id,
        total_games_played=total_games_played,
        total_wins=total_wins,
        win_percentage=win_percentage,
        total_losses=total_losses,
        loss_percentage=loss_percentage,
        playoff_goals_scored=playoff_and_championship_goals_scored,
        playoff_goals_against=playoff_and_championship_goals_against,
        playoff_goals_scored_percentage=playoff_goals_scored_percentage,
        playoff_goals_against_percentage=playoff_goals_against_percentage,
        playoff_games_played=playoff_games_played,
        playoff_wins=playoff_wins,
        playoff_win_percentage=playoff_win_percentage,
        playoff_losses=playoff_losses,
        playoff_loss_percentage=playoff_loss_percentage,
        championship_games_played=championship_games_played,
        championship_wins=championship_wins,
        championship_win_percentage=championship_win_percentage,
        championship_losses=championship_losses,
        championship_loss_percentage=championship_loss_percentage,
        best_performance=best_performance,
        worst_performance=worst_performance,
        long_timers=long_timers,
        last_division_name=last_division_name,
        recent_and_upcoming_games_data=recent_and_upcoming_games_data,  # Pass recent and upcoming games data to the template
        championship_wins_data=championship_wins_data  # Pass championship wins data to the template
    )