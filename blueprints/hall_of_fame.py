from flask import Blueprint, request, render_template
from hockey_blast_common_lib.models import db, Human
from hockey_blast_common_lib.stats_models import OrgStatsHuman

hall_of_fame_bp = Blueprint('hall_of_fame', __name__)

@hall_of_fame_bp.route('/hall_of_fame', methods=['GET'])
def hall_of_fame():
    top_n = request.args.get('top_n', default=20, type=int)
    
    # Fetch top humans based on game participation
    top_humans = db.session.query(Human, OrgStatsHuman).join(OrgStatsHuman, Human.id == OrgStatsHuman.human_id).order_by(OrgStatsHuman.games_skater.desc()).limit(top_n).all()
    
    # Prepare data for the template
    humans_data = []
    for rank, (human, stats) in enumerate(top_humans, start=1):
        humans_data.append({
            'rank': rank,
            'name': f"{human.first_name} {human.middle_name} {human.last_name}".strip(),
            'total': stats.games_skater,
            'skater': stats.games_skater,
            'goalie': stats.games_goalie,
            'referee': stats.games_referee,
            'scorekeeper': stats.games_scorekeeper
        })
    
    return render_template('hall_of_fame.html', top_humans=humans_data)
