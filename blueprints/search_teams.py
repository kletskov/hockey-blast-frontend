from flask import Blueprint, request, render_template, url_for
from hockey_blast_common_lib.models import db, Team
from options import MAX_TEAM_SEARCH_RESULTS
import urllib.parse

search_teams_bp = Blueprint('search_teams', __name__)

@search_teams_bp.route('/search_teams', methods=['GET', 'POST'])
def search_teams():
    if request.method == 'POST':
        team_name = request.form.get('team_name')
        print(f"Debug: Team name: {team_name}")
        query = db.session.query(Team)
        
        if team_name:
            query = query.filter(Team.name.ilike(f'%{team_name}%'))
        
        # Apply limit directly in the query
        results = query.limit(MAX_TEAM_SEARCH_RESULTS).all()
        
        if not results:
            return render_template('search_teams.html', no_results=True, max_results=MAX_TEAM_SEARCH_RESULTS)
        
        links = []
        for team in results:
            link_text = team.name
            encoded_link_text = urllib.parse.quote(link_text)
            link = f'<a href="{url_for("team_stats.team_stats", team_id=team.id)}">{link_text}</a>'
            links.append(link)
        
        return render_template('search_teams.html', results=links, max_results=MAX_TEAM_SEARCH_RESULTS)
    
    return render_template('search_teams.html', max_results=MAX_TEAM_SEARCH_RESULTS)