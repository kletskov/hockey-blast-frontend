import logging
from flask import Flask, render_template, request, g, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from threading import Thread
from hockey_blast_common_lib.models import db, Organization, Game, Human
from hockey_blast_common_lib.stats_models import OrgStatsDailySkater, OrgStatsWeeklySkater, OrgStatsDailyGoalie, OrgStatsWeeklyGoalie, OrgStatsDailyReferee, OrgStatsWeeklyReferee
from hockey_blast_common_lib.db_connection import get_db_params
from markupsafe import Markup
import flask_table.table
import flask_table.columns
from markupsafe import Markup
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

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
    app.register_blueprint(human_stats_bp)
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
    # @limiter.limit("1 per 1 seconds")
    # @user_agent_limiter.limit("1 per minute", key_func=lambda: BLOCKED_USER_AGENT)
    def index():
        try:
            top_n = request.args.get('top_n', default=3, type=int)
            org_id = request.args.get('org_id', default=1, type=int)
            organization = db.session.query(Organization).filter(Organization.id == org_id).first()
            # Query the total number of rows
            games_indexed = db.session.query(Game).count()
            
            # Query the latest date and time
            last_scheduled = db.session.query(Game).filter(Game.org_id == org_id).order_by(Game.date.desc(), Game.time.desc()).first()
            
            # Query the latest date and time where home_final_score is set
            last_played = db.session.query(Game).filter(Game.org_id == org_id, Game.status.startswith("Final")).order_by(Game.date.desc(), Game.time.desc()).first()
            
            # Format the time as HH:MM AM/PM
            last_scheduled_time = last_scheduled.time.strftime('%I:%M %p') if last_scheduled else None
            last_played_time = last_played.time.strftime('%I:%M %p') if last_played else None
            
            # Fetch top performers for the last day
            daily_skater_games_played = db.session.query(OrgStatsDailySkater, Human).join(Human, OrgStatsDailySkater.human_id == Human.id).filter(OrgStatsDailySkater.org_id == org_id, OrgStatsDailySkater.games_played > 0).order_by(OrgStatsDailySkater.games_played.desc()).limit(top_n).all()
            daily_skater_goals = db.session.query(OrgStatsDailySkater, Human).join(Human, OrgStatsDailySkater.human_id == Human.id).filter(OrgStatsDailySkater.org_id == org_id, OrgStatsDailySkater.goals > 0).order_by(OrgStatsDailySkater.goals.desc()).limit(top_n).all()
            daily_skater_assists = db.session.query(OrgStatsDailySkater, Human).join(Human, OrgStatsDailySkater.human_id == Human.id).filter(OrgStatsDailySkater.org_id == org_id, OrgStatsDailySkater.assists > 0).order_by(OrgStatsDailySkater.assists.desc()).limit(top_n).all()
            daily_skater_points = db.session.query(OrgStatsDailySkater, Human).join(Human, OrgStatsDailySkater.human_id == Human.id).filter(OrgStatsDailySkater.org_id == org_id, OrgStatsDailySkater.points > 0).order_by(OrgStatsDailySkater.points.desc()).limit(top_n).all()
            daily_skater_penalties = db.session.query(OrgStatsDailySkater, Human).join(Human, OrgStatsDailySkater.human_id == Human.id).filter(OrgStatsDailySkater.org_id == org_id, OrgStatsDailySkater.penalties > 0).order_by(OrgStatsDailySkater.penalties.desc()).limit(top_n).all()

            daily_goalie_games_played = db.session.query(OrgStatsDailyGoalie, Human).join(Human, OrgStatsDailyGoalie.human_id == Human.id).filter(OrgStatsDailyGoalie.org_id == org_id, OrgStatsDailyGoalie.games_played > 0).order_by(OrgStatsDailyGoalie.games_played.desc()).limit(top_n).all()
            daily_goalie_save_percentage = db.session.query(OrgStatsDailyGoalie, Human).join(Human, OrgStatsDailyGoalie.human_id == Human.id).filter(OrgStatsDailyGoalie.org_id == org_id, OrgStatsDailyGoalie.save_percentage > 0).order_by(OrgStatsDailyGoalie.save_percentage.desc()).limit(top_n).all()

            daily_referee_games_reffed = db.session.query(OrgStatsDailyReferee, Human).join(Human, OrgStatsDailyReferee.human_id == Human.id).filter(OrgStatsDailyReferee.org_id == org_id, OrgStatsDailyReferee.games_reffed > 0).order_by(OrgStatsDailyReferee.games_reffed.desc()).limit(top_n).all()
            daily_referee_penalties_given = db.session.query(OrgStatsDailyReferee, Human).join(Human, OrgStatsDailyReferee.human_id == Human.id).filter(OrgStatsDailyReferee.org_id == org_id, OrgStatsDailyReferee.penalties_given > 0).order_by(OrgStatsDailyReferee.penalties_given.desc()).limit(top_n).all()
            daily_referee_gm_given = db.session.query(OrgStatsDailyReferee, Human).join(Human, OrgStatsDailyReferee.human_id == Human.id).filter(OrgStatsDailyReferee.org_id == org_id, OrgStatsDailyReferee.gm_given > 0).order_by(OrgStatsDailyReferee.gm_given.desc()).limit(top_n).all()
            
            return render_template('index.html', games_indexed=games_indexed, last_scheduled=last_scheduled, last_scheduled_time=last_scheduled_time, last_played=last_played, last_played_time=last_played_time, background_image=app.config['BACKGROUND_IMAGE'], 
                                   daily_skater_games_played=daily_skater_games_played, daily_skater_goals=daily_skater_goals, daily_skater_assists=daily_skater_assists, daily_skater_points=daily_skater_points, daily_skater_penalties=daily_skater_penalties,
                                   daily_goalie_games_played=daily_goalie_games_played, daily_goalie_save_percentage=daily_goalie_save_percentage,
                                   daily_referee_games_reffed=daily_referee_games_reffed, daily_referee_penalties_given=daily_referee_penalties_given, daily_referee_gm_given=daily_referee_gm_given, org_name = organization.organization_name)
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
