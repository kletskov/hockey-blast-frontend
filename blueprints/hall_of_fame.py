from flask import Blueprint, request, render_template, url_for
from hockey_blast_common_lib.models import db, Human
from hockey_blast_common_lib.stats_models import OrgStatsHuman, OrgStatsSkater, OrgStatsGoalie, OrgStatsReferee, OrgStatsScorekeeper
from hockey_blast_common_lib.utils import get_fake_human_for_stats

from options import MAX_HUMAN_SEARCH_RESULTS

hall_of_fame_bp = Blueprint('hall_of_fame', __name__)

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

def get_top_goalies_data(session, org_id, category, top_n_stats=10):
    fake_human_id = get_fake_human_for_stats(session)
    top_players = session.query(OrgStatsGoalie, Human).join(Human, Human.id == OrgStatsGoalie.human_id).filter(
        OrgStatsGoalie.org_id == org_id,
        OrgStatsGoalie.human_id != fake_human_id,
        OrgStatsGoalie.human_id != 131183,
        OrgStatsGoalie.human_id != 131145,
        OrgStatsGoalie.games_played >= 100

    ).order_by(getattr(OrgStatsGoalie, category).desc()).limit(top_n_stats).all()
    
    return [
        {
            'rank': idx + 1,
            'name': f'<a href="{url_for("human_stats.human_stats", human_id=player.Human.id)}">{player.Human.first_name} {player.Human.middle_name} {player.Human.last_name}</a>',
            'value': getattr(player.OrgStatsGoalie, category)
        }
        for idx, player in enumerate(top_players)
    ]

def get_top_referees_data(session, org_id, category, top_n_stats=10):
    fake_human_id = get_fake_human_for_stats(session)
    top_players = session.query(OrgStatsReferee, Human).join(Human, Human.id == OrgStatsReferee.human_id).filter(
        OrgStatsReferee.org_id == org_id,
        OrgStatsReferee.human_id != fake_human_id,
        OrgStatsReferee.human_id != 131183,
        OrgStatsReferee.human_id != 131145,
        OrgStatsReferee.games_reffed >= 50
    ).order_by(getattr(OrgStatsReferee, category).desc()).limit(top_n_stats).all()
    
    return [
        {
            'rank': idx + 1,
            'name': f'<a href="{url_for("human_stats.human_stats", human_id=player.Human.id)}">{player.Human.first_name} {player.Human.middle_name} {player.Human.last_name}</a>',
            'value': getattr(player.OrgStatsReferee, category)
        }
        for idx, player in enumerate(top_players)
    ]

def get_top_scorekeepers_data(session, org_id, category, top_n_stats=10):
    fake_human_id = get_fake_human_for_stats(session)
    top_players = session.query(OrgStatsScorekeeper, Human).join(Human, Human.id == OrgStatsScorekeeper.human_id).filter(
        OrgStatsScorekeeper.org_id == org_id,
        OrgStatsScorekeeper.human_id != fake_human_id,
        OrgStatsScorekeeper.games_recorded >= 50
    ).order_by(getattr(OrgStatsScorekeeper, category).desc()).limit(top_n_stats).all()
    
    return [
        {
            'rank': idx + 1,
            'name': f'<a href="{url_for("human_stats.human_stats", human_id=player.Human.id)}">{player.Human.first_name} {player.Human.middle_name} {player.Human.last_name}</a>',
            'value': getattr(player.OrgStatsScorekeeper, category)
        }
        for idx, player in enumerate(top_players)
    ]

def get_top_humans_data(session, org_id, top_n_stats=10):
    fake_human_id = get_fake_human_for_stats(session)
    top_humans = session.query(OrgStatsHuman, Human).join(Human, Human.id == OrgStatsHuman.human_id).filter(
        OrgStatsHuman.org_id == org_id,
        OrgStatsHuman.human_id != 131183,
        OrgStatsHuman.human_id != 131145,
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


@hall_of_fame_bp.route('/hall_of_fame', methods=['GET'])
def hall_of_fame():
    org_id = -1
    top_n_stats = request.args.get('top_n', default=10)
  
    # Fetch top skaters in different categories
    top_games_played_data = get_top_skaters_data(db.session, org_id, 'games_played', top_n_stats)
    top_goals_data = get_top_skaters_data(db.session, org_id, 'goals', top_n_stats)
    top_points_data = get_top_skaters_data(db.session, org_id, 'points', top_n_stats)
    top_points_per_game_data = get_top_skaters_data(db.session, org_id, 'points_per_game', top_n_stats)
    top_penalties_per_game_data = get_top_skaters_data(db.session, org_id, 'penalties_per_game', top_n_stats)
    
    # Fetch top goalies in different categories
    top_goalies_data = get_top_goalies_data(db.session, org_id, 'games_played', top_n_stats)
    top_goalies_save_percentage_data = get_top_goalies_data(db.session, org_id, 'save_percentage', top_n_stats)
    
    # Fetch top referees in different categories
    top_referees_data = get_top_referees_data(db.session, org_id, 'games_reffed', top_n_stats)
    
    # Fetch top scorekeepers in different categories
    top_scorekeepers_data = get_top_scorekeepers_data(db.session, org_id, 'games_recorded', top_n_stats)
    
    humans_data = get_top_humans_data(db.session, org_id, top_n_stats)
    
    return render_template('hall_of_fame.html', top_humans=humans_data, top_games_played=top_games_played_data, top_goals=top_goals_data, top_points=top_points_data, top_points_per_game=top_points_per_game_data, top_penalties_per_game=top_penalties_per_game_data, top_goalies=top_goalies_data, top_goalies_save_percentage=top_goalies_save_percentage_data, top_referees=top_referees_data, top_scorekeepers=top_scorekeepers_data)
