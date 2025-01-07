import sys, os
from flask import Blueprint, request, render_template, url_for

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hockey_blast_common_lib.models import db, Human, HumanAlias
from hockey_blast_common_lib.stats_models import OrgStatsHuman, OrgStatsSkater
from options import MAX_HUMAN_SEARCH_RESULTS

search_players_bp = Blueprint('search_humans', __name__)

def get_fake_human_for_stats(session):
    first_name = "Fake"
    middle_name = "Stats"
    last_name = "Human"

    # Check if the human already exists
    existing_human = session.query(Human).filter_by(first_name=first_name, middle_name=middle_name, last_name=last_name).first()
    if existing_human:
        return existing_human.id
    
    return None

def get_top_skaters_data(session, org_id, category, top_n_stats=10):
    fake_human_id = get_fake_human_for_stats(session)
    top_players = session.query(OrgStatsSkater, Human).join(Human, Human.id == OrgStatsSkater.human_id).filter(
        OrgStatsSkater.org_id == org_id,
        OrgStatsSkater.human_id != fake_human_id,
        OrgStatsSkater.games_played >= 50
    ).order_by(getattr(OrgStatsSkater, category).desc()).limit(top_n_stats).all()
    
    return [
        {
            'rank': idx + 1,
            'name': f'<a href="{url_for("human_stats.human_stats", human_id=player.Human.id)}">{player.Human.first_name} {player.Human.middle_name} {player.Human.last_name}</a>',
            'value': getattr(player.OrgStatsSkater, category)
        }
        for idx, player in enumerate(top_players)
    ]

def get_top_humans_data(session, org_id, top_n_stats=10):
    fake_human_id = get_fake_human_for_stats(session)
    top_humans = session.query(OrgStatsHuman, Human).join(Human, Human.id == OrgStatsHuman.human_id).filter(
        OrgStatsHuman.org_id == org_id,
        OrgStatsHuman.human_id != fake_human_id
    ).order_by(OrgStatsHuman.games_total.desc()).limit(top_n_stats).all()
    
    return [
        {
            'rank': idx + 1,
            'name': f'<a href="{url_for("human_stats.human_stats", human_id=human.Human.id)}">{human.Human.first_name} {human.Human.middle_name} {human.Human.last_name}</a>',
            'total': human.OrgStatsHuman.games_total,
            'skater': human.OrgStatsHuman.games_skater,
            'goalie': human.OrgStatsHuman.games_goalie,
            'referee': human.OrgStatsHuman.games_referee,
            'scorekeeper': human.OrgStatsHuman.games_scorekeeper
        }
        for idx, human in enumerate(top_humans)
    ]

@search_players_bp.route('/search_humans', methods=['GET', 'POST'])
def search_humans():
    org_id = 1
    top_n_stats = 10

    # Fetch top humans by total games
    top_humans_data = get_top_humans_data(db.session, org_id, top_n_stats)

    # Fetch top skaters in different categories
    top_games_played_data = get_top_skaters_data(db.session, org_id, 'games_played', top_n_stats)
    top_points_per_game_data = get_top_skaters_data(db.session, org_id, 'points_per_game', top_n_stats)
    top_penalties_per_game_data = get_top_skaters_data(db.session, org_id, 'penalties_per_game', top_n_stats)

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        print(f"Debug: First name: {first_name}, Last name: {last_name}")
        query = db.session.query(Human)
        
        if first_name:
            query = query.filter(Human.first_name.ilike(f'%{first_name}%'))
        if last_name:
            query = query.filter(Human.last_name.ilike(f'%{last_name}%'))
        
        # Apply limit directly in the query
        results = query.limit(MAX_HUMAN_SEARCH_RESULTS).all()
        
        if not results:
            return render_template('search_humans.html', no_results=True, max_results=MAX_HUMAN_SEARCH_RESULTS, top_humans=top_humans_data, top_games_played=top_games_played_data, top_points_per_game=top_points_per_game_data, top_penalties_per_game=top_penalties_per_game_data)
        
        links = []
        for player in results:
            print(f"Debug: Player ID: {player.id}")
            aliases = db.session.query(HumanAlias).filter(HumanAlias.human_id == player.id).all()
            alias_names = [f"{alias.first_name} {alias.middle_name} {alias.last_name}".strip() for alias in aliases if f"{alias.first_name} {alias.middle_name} {alias.last_name}".strip() != f"{player.first_name} {player.middle_name} {player.last_name}".strip()]
            alias_text = f" A.K.A. {', '.join(alias_names)}" if alias_names else ""
            link_text = f"{player.first_name} {player.middle_name} {player.last_name}{alias_text}"
            link = f'<a href="{url_for("human_stats.human_stats", human_id=player.id, top_n=20)}">{link_text}</a>'
            links.append(link)
        
        return render_template('search_humans.html', results=links, max_results=MAX_HUMAN_SEARCH_RESULTS, top_humans=top_humans_data, top_games_played=top_games_played_data, top_points_per_game=top_points_per_game_data, top_penalties_per_game=top_penalties_per_game_data)
    
    return render_template('search_humans.html', max_results=MAX_HUMAN_SEARCH_RESULTS, top_humans=top_humans_data, top_games_played=top_games_played_data, top_points_per_game=top_points_per_game_data, top_penalties_per_game=top_penalties_per_game_data)

# session = create_session('sharksice')
# category = 'games_played'
# top_games_played_data = get_top_players_data(session, 1, category, 10)
# print(f"For category '{category}', top players are:")
# for player in top_games_played_data:
#     print(f"{player['rank']}. {player['name']}: {player['value']} games played")