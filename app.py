import logging
from flask import Flask, render_template, request, g, jsonify, send_from_directory, url_for, redirect
from flask_restx import Api
from flask_sqlalchemy import SQLAlchemy
from threading import Thread
from hockey_blast_common_lib.models import db, Organization, Game, Human, RequestLog, Team, HumanAlias
from hockey_blast_common_lib.stats_models import OrgStatsWeeklyHuman, OrgStatsDailySkater, OrgStatsWeeklySkater, OrgStatsDailyGoalie, OrgStatsWeeklyGoalie, OrgStatsDailyReferee, OrgStatsWeeklyReferee, OrgStatsSkater, OrgStatsGoalie, OrgStatsReferee, OrgStatsDailyHuman, OrgStatsHuman
from hockey_blast_common_lib.db_connection import get_db_params
from markupsafe import Markup
import flask_table.table
import flask_table.columns
from markupsafe import Markup
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from hockey_blast_common_lib.utils import get_fake_human_for_stats
from datetime import datetime, timezone, timedelta
import psycopg2
from hockey_blast_common_lib.stats_utils import ALL_ORGS_ID
from options import MAX_TEAM_SEARCH_RESULTS
from options import MAX_HUMAN_SEARCH_RESULTS
import urllib.parse

# Debug: Print the DB_HOST environment variable
flask_table.table.Markup = Markup
flask_table.columns.Markup = Markup

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from blueprints.teams_per_season import teams_per_season_bp
from blueprints.human_stats import human_stats_bp
from blueprints.hall_of_fame import hall_of_fame_bp
from blueprints.players_per_season import players_per_season_bp
from blueprints.active_players import active_players_bp
from blueprints.day_of_week import day_of_week_bp
from blueprints.time_of_games import time_of_games_bp
from blueprints.search_teams import search_teams_bp
from blueprints.team_stats import team_stats_bp
from blueprints.game_card import game_card_bp
from blueprints.seasons import seasons_bp
from blueprints.game_shootout import game_shootout_bp
from blueprints.version import version_bp
from blueprints.dropdowns import dropdowns_bp
from blueprints.games import games_bp
from blueprints.about import about_bp
from blueprints.penalties import penalties_bp
from blueprints.skater_performance import skater_performance_bp
from blueprints.goalie_performance import goalie_performance_bp
from blueprints.request_logs import request_logs_bp

from api.v1.organizations import organizations_ns
from api.v1.divisions import divisions_ns

# BLOCKED_USER_AGENT = "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.6834.83 Mobile Safari/537.36 (compatible; GoogleOther)"
# BLOCKED_IPS = ["66.249.72.103", "66.249.72.204"]

def get_user_agent():
    return request.headers.get('User-Agent')

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr


def create_app(db_name):
    app = Flask(__name__)
    db_params = get_db_params(db_name)
    db_url = f"postgresql://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_params['dbname']}"
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['BACKGROUND_IMAGE'] = 'default_background.jpg'
    app.config['ORG_NAME'] = 'Hockey Blast'
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(teams_per_season_bp)
    app.register_blueprint(human_stats_bp, url_prefix='/human_stats')
    app.register_blueprint(hall_of_fame_bp, url_prefix='/hall_of_fame')
    app.register_blueprint(players_per_season_bp)
    app.register_blueprint(seasons_bp)
    app.register_blueprint(active_players_bp)
    app.register_blueprint(day_of_week_bp)
    app.register_blueprint(time_of_games_bp)
    app.register_blueprint(search_teams_bp)
    app.register_blueprint(team_stats_bp)
    app.register_blueprint(game_card_bp)
    app.register_blueprint(game_shootout_bp)
    app.register_blueprint(version_bp)
    app.register_blueprint(games_bp, url_prefix='/games')
    app.register_blueprint(dropdowns_bp, url_prefix='/dropdowns')
    app.register_blueprint(about_bp)
    app.register_blueprint(penalties_bp, url_prefix='/penalties')
    app.register_blueprint(skater_performance_bp, url_prefix='/skater_performance')
    app.register_blueprint(goalie_performance_bp, url_prefix='/goalie_performance')
    app.register_blueprint(request_logs_bp, url_prefix='/request_logs')

    @app.before_request
    def before_request():
        if request.path in ['/favicon.ico', '/dropdowns', '/dropdowns/filter_levels', '/dropdowns/filter_seasons', '/games/filter_games']:
            return
        try:
            user_agent = request.headers.get('User-Agent')
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            path = request.path
            cgi_params = request.query_string.decode('utf-8')  # Get CGI parameters
            pst = timezone(timedelta(hours=-8))
            timestamp = datetime.now(pst)

            log_entry = RequestLog(
                user_agent=user_agent,
                client_ip=client_ip,
                path=path,
                timestamp=timestamp,
                cgi_params=cgi_params  # Log CGI parameters
            )
            db.session.add(log_entry)
            db.session.commit()
        except psycopg2.errors.InsufficientPrivilege as e:
            db.session.rollback()
            logger.error(f"Failed to log request: {e}. User '{db_params['user']}' does not have permission to access the table.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to log request: {e}")


    @app.route('/', methods=['GET', 'POST'])
    def index():
        try:
            top_n = request.args.get('top_n', default=10, type=int)

            # Redirect to include top_n in the URL if not present
            if 'top_n' not in request.args:
                return redirect(url_for('index', top_n=top_n))

            # Fetch the latest date and time
            last_scheduled = db.session.query(Game).order_by(Game.date.desc(), Game.time.desc()).first()
            last_played = db.session.query(Game).filter(Game.status.startswith("Final")).order_by(Game.date.desc(), Game.time.desc()).first()

            # Format the time as HH:MM AM/PM
            last_scheduled_time = last_scheduled.time.strftime('%I:%M %p') if last_scheduled else None
            last_played_time = last_played.time.strftime('%I:%M %p') if last_played else None

            # Get the fake human ID to exclude from scorekeeper stats
            fake_human_id = get_fake_human_for_stats(db.session)

            # Fetch top performers for the last day
            daily_skater_points = db.session.query(OrgStatsDailySkater, Human, Organization).join(Human, OrgStatsDailySkater.human_id == Human.id).join(Organization, OrgStatsDailySkater.org_id == Organization.id).filter(OrgStatsDailySkater.points > 0, OrgStatsDailySkater.org_id != ALL_ORGS_ID).order_by(OrgStatsDailySkater.points.desc()).limit(top_n).all()
            daily_goalie_games_played = db.session.query(OrgStatsDailyGoalie, Human, Organization).join(Human, OrgStatsDailyGoalie.human_id == Human.id).join(Organization, OrgStatsDailyGoalie.org_id == Organization.id).filter(OrgStatsDailyGoalie.games_played > 0, OrgStatsDailyGoalie.org_id != ALL_ORGS_ID).order_by(OrgStatsDailyGoalie.games_played.desc(), OrgStatsDailyGoalie.save_percentage.desc()).limit(top_n).all()
            daily_referee_games_reffed = db.session.query(OrgStatsDailyReferee, Human, Organization).join(Human, OrgStatsDailyReferee.human_id == Human.id).join(Organization, OrgStatsDailyReferee.org_id == Organization.id).filter(OrgStatsDailyReferee.games_reffed > 0, OrgStatsDailyReferee.org_id != ALL_ORGS_ID).order_by(OrgStatsDailyReferee.games_reffed.desc(), (OrgStatsDailyReferee.gm_given + OrgStatsDailyReferee.penalties_given).desc()).limit(top_n).all()
            daily_scorekeeper_games = db.session.query(OrgStatsDailyHuman, Human, Organization).join(Human, OrgStatsDailyHuman.human_id == Human.id).join(Organization, OrgStatsDailyHuman.org_id == Organization.id).filter(OrgStatsDailyHuman.games_scorekeeper > 0, OrgStatsDailyHuman.human_id != fake_human_id, OrgStatsDailyHuman.org_id != ALL_ORGS_ID).order_by(OrgStatsDailyHuman.games_scorekeeper.desc()).limit(top_n).all()

            # Fetch top performers for the last week
            weekly_skater_points = db.session.query(OrgStatsWeeklySkater, Human, Organization).join(Human, OrgStatsWeeklySkater.human_id == Human.id).join(Organization, OrgStatsWeeklySkater.org_id == Organization.id).filter(OrgStatsWeeklySkater.points > 0, OrgStatsWeeklySkater.org_id != ALL_ORGS_ID).order_by(OrgStatsWeeklySkater.points.desc()).limit(top_n).all()
            weekly_goalie_games_played = db.session.query(OrgStatsWeeklyGoalie, Human, Organization).join(Human, OrgStatsWeeklyGoalie.human_id == Human.id).join(Organization, OrgStatsWeeklyGoalie.org_id == Organization.id).filter(OrgStatsWeeklyGoalie.games_played > 0, OrgStatsWeeklyGoalie.org_id != ALL_ORGS_ID).order_by(OrgStatsWeeklyGoalie.games_played.desc(), OrgStatsWeeklyGoalie.save_percentage.desc()).limit(top_n).all()
            weekly_referee_games_reffed = db.session.query(OrgStatsWeeklyReferee, Human, Organization).join(Human, OrgStatsWeeklyReferee.human_id == Human.id).join(Organization, OrgStatsWeeklyReferee.org_id == Organization.id).filter(OrgStatsWeeklyReferee.games_reffed > 0, OrgStatsWeeklyReferee.org_id != ALL_ORGS_ID).order_by(OrgStatsWeeklyReferee.games_reffed.desc(), (OrgStatsWeeklyReferee.gm_given + OrgStatsWeeklyReferee.penalties_given).desc()).limit(top_n).all()
            weekly_scorekeeper_games = db.session.query(OrgStatsWeeklyHuman, Human, Organization).join(Human, OrgStatsWeeklyHuman.human_id == Human.id).join(Organization, OrgStatsWeeklyHuman.org_id == Organization.id).filter(OrgStatsWeeklyHuman.games_scorekeeper > 0, OrgStatsWeeklyHuman.human_id != fake_human_id, OrgStatsWeeklyHuman.org_id != ALL_ORGS_ID).order_by(OrgStatsWeeklyHuman.games_scorekeeper.desc()).limit(top_n).all()

            if request.method == 'POST':
                team_name = request.form.get('team_name')
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
                else:
                        first_name = request.form.get('first_name')
                        last_name = request.form.get('last_name')
                        query = db.session.query(Human)

                        if first_name:
                            query = query.filter(Human.first_name.ilike(f'%{first_name}%'))
                        if last_name:
                            query = query.filter(Human.last_name.ilike(f'%{last_name}%'))

                        # Apply limit directly in the query
                        results = query.limit(MAX_HUMAN_SEARCH_RESULTS).all()

                        links = []
                        for player in results:
                            aliases = db.session.query(HumanAlias).filter(HumanAlias.human_id == player.id).all()
                            alias_names = [f"{alias.first_name} {alias.middle_name} {alias.last_name}".strip() for alias in aliases if f"{alias.first_name} {alias.middle_name} {alias.last_name}".strip() != f"{player.first_name} {player.middle_name} {player.last_name}".strip()]
                            alias_text = f" A.K.A. {', '.join(alias_names)}" if alias_names else ""
                            link_text = f"{player.first_name} {player.middle_name} {player.last_name}{alias_text}"
                            link = f'<a href="{url_for("human_stats.human_stats", human_id=player.id, top_n=20)}">{link_text}</a>'
                            links.append(link)

                return render_template('index.html',
                                       search_results=links,
                                last_scheduled=last_scheduled, last_scheduled_time=last_scheduled_time, last_played=last_played, last_played_time=last_played_time,
                                daily_skater_points=daily_skater_points, daily_goalie_games_played=daily_goalie_games_played, daily_referee_games_reffed=daily_referee_games_reffed, daily_scorekeeper_games=daily_scorekeeper_games,
                                weekly_skater_points=weekly_skater_points, weekly_goalie_games_played=weekly_goalie_games_played, weekly_referee_games_reffed=weekly_referee_games_reffed, weekly_scorekeeper_games=weekly_scorekeeper_games)
            return render_template('index.html',
                                search_results=None,
                                last_scheduled=last_scheduled, last_scheduled_time=last_scheduled_time, last_played=last_played, last_played_time=last_played_time,
                                daily_skater_points=daily_skater_points, daily_goalie_games_played=daily_goalie_games_played, daily_referee_games_reffed=daily_referee_games_reffed, daily_scorekeeper_games=daily_scorekeeper_games,
                                weekly_skater_points=weekly_skater_points, weekly_goalie_games_played=weekly_goalie_games_played, weekly_referee_games_reffed=weekly_referee_games_reffed, weekly_scorekeeper_games=weekly_scorekeeper_games)
        except Exception as e:
            error_info = {
                "error": str(e),
                "db_params": {**db_params, "password": "HIDDEN"}
            }
            return render_template('error.html', error_info=error_info)

    @app.route('/special_stats')
    def special_stats():
        return render_template('special_stats.html', background_image=app.config['BACKGROUND_IMAGE'])

    @app.route('/robots.txt')
    def robots_txt():
        return send_from_directory(app.root_path, 'robots.txt')

    @app.route('/about')
    def about():
        return render_template('about.html')

    api = Api(
        app,
        version='1.0',
        title='Hockey BLAST API',
        description='RESTful API',
        doc='/swagger'
    )

    api.add_namespace(organizations_ns, path='/api/v1')
    api.add_namespace(divisions_ns, path='/api/v1')

    return app

def run_app(app, port):
    app.run(host='0.0.0.0', port=port, debug=True)

if __name__ == "__main__":
    app1 = create_app("frontend")
    thread1 = Thread(target=run_app, args=(app1, 5000))
    thread1.start()
    thread1.join()

    # app2 = create_app("frontend-sample-db")
    # thread2 = Thread(target=run_app, args=(app2, 5005))
    # thread2.start()
    # thread2.join()
