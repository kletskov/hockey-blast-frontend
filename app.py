import logging
from flask import Flask, render_template, request, g, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from threading import Thread
from hockey_blast_common_lib.models import db, Organization, Game, Human
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

# Debug: Print the DB_HOST environment variable
flask_table.table.Markup = Markup
flask_table.columns.Markup = Markup

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from blueprints.teams_per_season import teams_per_season_bp
from blueprints.human_stats import human_stats_bp
from blueprints.search_humans import search_players_bp
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
    
    # Initialize Limiter
    # limiter = Limiter(
    #     key_func=get_client_ip,
    #     app=app,
    #     default_limits=["1 per 2 seconds", "1000 per day"]
    # )
    
    # Custom limit for specific user agent
    # user_agent_limiter = Limiter(
    #     key_func=get_user_agent,
    #     app=app,
    #     default_limits=["1 per minute"]
    # )
    
    # Register blueprints
    app.register_blueprint(teams_per_season_bp)
    app.register_blueprint(human_stats_bp, url_prefix='/human_stats')
    app.register_blueprint(search_players_bp)
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
    
    # @app.before_request
    # def before_request():
    #     g.limited = False
    #     user_agent = get_user_agent()
    #     client_ip = get_client_ip()
    #     logger.info(f"Request from {client_ip} with User-Agent {user_agent}")
    #     # if user_agent == BLOCKED_USER_AGENT or client_ip in BLOCKED_IPS:
    #     #     logger.warning(f"Blocked request from {client_ip} with User-Agent {user_agent}")
    #     #     return jsonify({"error": "Request blocked"}), 403

    # @app.after_request
    # def after_request(response):
    #     client_ip = get_client_ip()
    #     if response.status_code == 429:
    #         g.limited = True
    #     logger.info(f"Request to {request.path} from {client_ip} with User-Agent {request.headers.get('User-Agent')} - Status: {response.status_code} - Limited: {g.limited}")
    #     return response
    
    @app.route('/')
    def index():
        try:
            top_n = request.args.get('top_n', default=5, type=int)
            
            # Fetch the latest date and time
            last_scheduled = db.session.query(Game).order_by(Game.date.desc(), Game.time.desc()).first()
            last_played = db.session.query(Game).filter(Game.status.startswith("Final")).order_by(Game.date.desc(), Game.time.desc()).first()
            
            # Format the time as HH:MM AM/PM
            last_scheduled_time = last_scheduled.time.strftime('%I:%M %p') if last_scheduled else None
            last_played_time = last_played.time.strftime('%I:%M %p') if last_played else None

            # Get the fake human ID to exclude from scorekeeper stats
            fake_human_id = get_fake_human_for_stats(db.session)

            # Fetch top performers for the last day
            daily_skater_points = db.session.query(OrgStatsDailySkater, Human, Organization).join(Human, OrgStatsDailySkater.human_id == Human.id).join(Organization, OrgStatsDailySkater.org_id == Organization.id).filter(OrgStatsDailySkater.points > 0).order_by(OrgStatsDailySkater.points.desc()).limit(top_n).all()
            daily_goalie_games_played = db.session.query(OrgStatsDailyGoalie, Human, Organization).join(Human, OrgStatsDailyGoalie.human_id == Human.id).join(Organization, OrgStatsDailyGoalie.org_id == Organization.id).filter(OrgStatsDailyGoalie.games_played > 0).order_by(OrgStatsDailyGoalie.games_played.desc(), OrgStatsDailyGoalie.save_percentage.desc()).limit(top_n).all()
            daily_referee_games_reffed = db.session.query(OrgStatsDailyReferee, Human, Organization).join(Human, OrgStatsDailyReferee.human_id == Human.id).join(Organization, OrgStatsDailyReferee.org_id == Organization.id).filter(OrgStatsDailyReferee.games_reffed > 0).order_by(OrgStatsDailyReferee.games_reffed.desc(), (OrgStatsDailyReferee.gm_given + OrgStatsDailyReferee.penalties_given).desc()).limit(top_n).all()
            daily_scorekeeper_games = db.session.query(OrgStatsDailyHuman, Human, Organization).join(Human, OrgStatsDailyHuman.human_id == Human.id).join(Organization, OrgStatsDailyHuman.org_id == Organization.id).filter(OrgStatsDailyHuman.games_scorekeeper > 0, OrgStatsDailyHuman.human_id != fake_human_id).order_by(OrgStatsDailyHuman.games_scorekeeper.desc()).limit(top_n).all()

            # Fetch top performers for the last week
            weekly_skater_points = db.session.query(OrgStatsWeeklySkater, Human, Organization).join(Human, OrgStatsWeeklySkater.human_id == Human.id).join(Organization, OrgStatsWeeklySkater.org_id == Organization.id).filter(OrgStatsWeeklySkater.points > 0).order_by(OrgStatsWeeklySkater.points.desc()).limit(top_n).all()
            weekly_goalie_games_played = db.session.query(OrgStatsWeeklyGoalie, Human, Organization).join(Human, OrgStatsWeeklyGoalie.human_id == Human.id).join(Organization, OrgStatsWeeklyGoalie.org_id == Organization.id).filter(OrgStatsWeeklyGoalie.games_played > 0).order_by(OrgStatsWeeklyGoalie.games_played.desc(), OrgStatsWeeklyGoalie.save_percentage.desc()).limit(top_n).all()
            weekly_referee_games_reffed = db.session.query(OrgStatsWeeklyReferee, Human, Organization).join(Human, OrgStatsWeeklyReferee.human_id == Human.id).join(Organization, OrgStatsWeeklyReferee.org_id == Organization.id).filter(OrgStatsWeeklyReferee.games_reffed > 0).order_by(OrgStatsWeeklyReferee.games_reffed.desc(), (OrgStatsWeeklyReferee.gm_given + OrgStatsWeeklyReferee.penalties_given).desc()).limit(top_n).all()
            weekly_scorekeeper_games = db.session.query(OrgStatsWeeklyHuman, Human, Organization).join(Human, OrgStatsWeeklyHuman.human_id == Human.id).join(Organization, OrgStatsWeeklyHuman.org_id == Organization.id).filter(OrgStatsWeeklyHuman.games_scorekeeper > 0, OrgStatsWeeklyHuman.human_id != fake_human_id).order_by(OrgStatsWeeklyHuman.games_scorekeeper.desc()).limit(top_n).all()

            # Fetch all-time top performers
            all_time_skater_points = db.session.query(OrgStatsSkater, Human, Organization).join(Human, OrgStatsSkater.human_id == Human.id).join(Organization, OrgStatsSkater.org_id == Organization.id).filter(OrgStatsSkater.points > 0).order_by(OrgStatsSkater.points.desc()).limit(top_n).all()
            all_time_goalie_games_played = db.session.query(OrgStatsGoalie, Human, Organization).join(Human, OrgStatsGoalie.human_id == Human.id).join(Organization, OrgStatsGoalie.org_id == Organization.id).filter(OrgStatsGoalie.games_played > 0).order_by(OrgStatsGoalie.games_played.desc(), OrgStatsGoalie.save_percentage.desc()).limit(top_n).all()
            all_time_referee_games_reffed = db.session.query(OrgStatsReferee, Human, Organization).join(Human, OrgStatsReferee.human_id == Human.id).join(Organization, OrgStatsReferee.org_id == Organization.id).filter(OrgStatsReferee.games_reffed > 0).order_by(OrgStatsReferee.games_reffed.desc(), (OrgStatsReferee.gm_given + OrgStatsReferee.penalties_given).desc()).limit(top_n).all()
            all_time_scorekeeper_games = db.session.query(OrgStatsHuman, Human, Organization).join(Human, OrgStatsHuman.human_id == Human.id).join(Organization, OrgStatsHuman.org_id == Organization.id).filter(OrgStatsHuman.games_scorekeeper > 0, OrgStatsHuman.human_id != fake_human_id).order_by(OrgStatsHuman.games_scorekeeper.desc()).limit(top_n).all()

            return render_template('index.html', 
                                   last_scheduled=last_scheduled, last_scheduled_time=last_scheduled_time, last_played=last_played, last_played_time=last_played_time,
                                   daily_skater_points=daily_skater_points, daily_goalie_games_played=daily_goalie_games_played, daily_referee_games_reffed=daily_referee_games_reffed, daily_scorekeeper_games=daily_scorekeeper_games,
                                   weekly_skater_points=weekly_skater_points, weekly_goalie_games_played=weekly_goalie_games_played, weekly_referee_games_reffed=weekly_referee_games_reffed, weekly_scorekeeper_games=weekly_scorekeeper_games,
                                   all_time_skater_points=all_time_skater_points, all_time_goalie_games_played=all_time_goalie_games_played, all_time_referee_games_reffed=all_time_referee_games_reffed, all_time_scorekeeper_games=all_time_scorekeeper_games)
        except Exception as e:
            error_info = {
                "error": str(e),
                "db_params": {**db_params, "password": "HIDDEN"}
            }
            return render_template('error.html', error_info=error_info)

    @app.route('/special_stats')
    # @limiter.limit("1 per 2 seconds")
    # @limiter.limit("1000 per day")
    # @user_agent_limiter.limit("1 per minute", key_func=lambda: BLOCKED_USER_AGENT)
    def special_stats():
        # Your logic to get any data needed for special_stats.html
        return render_template('special_stats.html', background_image=app.config['BACKGROUND_IMAGE'])

    @app.route('/robots.txt')
    def robots_txt():
        return send_from_directory(app.root_path, 'robots.txt')

    @app.route('/about')
    def about():
        return render_template('about.html')

    return app

def run_app(app, port):
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    app1 = create_app("frontend")
    thread1 = Thread(target=run_app, args=(app1, 5000))
    thread1.start()
    thread1.join()

    # app2 = create_app("frontend-sample-db")
    # thread2 = Thread(target=run_app, args=(app2, 5005))
    # thread2.start()
    # thread2.join()
