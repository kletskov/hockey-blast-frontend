"""
Playoff brackets — /playoffs and /api/playoffs
"""
import logging
from flask import Blueprint, render_template, jsonify
from sqlalchemy import text

logger = logging.getLogger(__name__)
playoffs_bp = Blueprint("playoffs", __name__)

ROUND_ORDER = {
    'Round Robin': 0, 'Qualifier': 1,
    'Playoff': 2, 'Quarter-Final': 3, 'Quater Final': 3,
    'Semi-Final': 4, 'Semi Final': 4,
    'Consolation': 5, 'Championship': 6,
}

@playoffs_bp.route("/playoffs")
def playoffs():
    return render_template("playoffs.html")

@playoffs_bp.route("/api/playoffs")
def playoffs_api():
    from hockey_blast_common_lib.models import db
    sql = text("""
        SELECT
            g.id as game_id, g.game_type, g.date::text, g.time::text,
            g.status, g.home_final_score, g.visitor_final_score,
            ht.id as home_team_id, ht.name as home_team,
            vt.id as visitor_team_id, vt.name as visitor_team,
            COALESCE(l.level_name, 'Unknown') as level_name,
            COALESCE(l.short_name, '') as level_short,
            d.id as division_id,
            COALESCE(l.skill_value, 999) as skill_value
        FROM games g
        JOIN teams ht ON ht.id = g.home_team_id
        JOIN teams vt ON vt.id = g.visitor_team_id
        JOIN divisions d ON d.id = g.division_id
        LEFT JOIN levels l ON l.id = d.level_id
        WHERE g.org_id = 1
        AND g.game_type IN ('Playoff','Semi-Final','Semi Final','Quarter-Final','Quater Final','Championship','Consolation','Qualifier','Round Robin')
        AND g.date >= CURRENT_DATE - INTERVAL '60 days'
        ORDER BY COALESCE(l.skill_value,999) ASC, d.id, g.date
    """)
    rows = db.session.execute(sql).fetchall()

    # Group by level → division → round
    levels = {}
    for r in rows:
        lname = r.level_name
        if lname not in levels:
            levels[lname] = {'name': lname, 'short': r.level_short, 'skill': r.skill_value, 'divisions': {}}
        divs = levels[lname]['divisions']
        did = r.division_id
        if did not in divs:
            divs[did] = {}
        rname = r.game_type
        if rname not in divs[did]:
            divs[did][rname] = []

        home_score = r.home_final_score
        visitor_score = r.visitor_final_score
        if home_score is not None and visitor_score is not None:
            score = f"{home_score}–{visitor_score}"
            if home_score > visitor_score:
                winner = r.home_team
            elif visitor_score > home_score:
                winner = r.visitor_team
            else:
                winner = None
        else:
            score = 'TBD'
            winner = None

        divs[did][rname].append({
            'game_id': r.game_id,
            'home_team': r.home_team,
            'home_team_id': r.home_team_id,
            'visitor_team': r.visitor_team,
            'visitor_team_id': r.visitor_team_id,
            'score': score,
            'winner': winner,
            'status': r.status,
            'date': r.date,
            'time': r.time,
            'game_type': r.game_type,
        })

    # Convert to sorted list
    result = []
    for lname, ldata in sorted(levels.items(), key=lambda x: x[1]['skill']):
        level_out = {'name': ldata['name'], 'short': ldata['short'], 'divisions': []}
        for did, rounds in ldata['divisions'].items():
            rounds_out = []
            for rname, games in sorted(rounds.items(), key=lambda x: ROUND_ORDER.get(x[0], 99)):
                rounds_out.append({'round_name': rname, 'games': games})
            level_out['divisions'].append({'division_id': did, 'rounds': rounds_out})
        result.append(level_out)

    return jsonify({'levels': result})
