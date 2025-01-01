from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
# import matplotlib
# matplotlib.use('Agg')
# import matplotlib.pyplot as plt
from threading import Thread
from hockey_blast_common_lib.models import db, Organization, Game, OrgStatsDailySkater, OrgStatsWeeklySkater, OrgStatsDailyGoalie, OrgStatsWeeklyGoalie, OrgStatsDailyReferee, OrgStatsWeeklyReferee, Human
from hockey_blast_common_lib.db_connection import get_db_params
from markupsafe import Markup

import flask_table.table
import flask_table.columns
from markupsafe import Markup

flask_table.table.Markup = Markup
flask_table.columns.Markup = Markup


from blueprints.teams_per_season import teams_per_season_bp
from blueprints.human_stats import human_stats_bp
from blueprints.search_humans import search_players_bp
from players_per_season import players_per_season_bp
from blueprints.active_players import active_players_bp
from blueprints.day_of_week import day_of_week_bp
from blueprints.time_of_games import time_of_games_bp
from blueprints.search_teams import search_teams_bp
from blueprints.team_stats import team_stats_bp
from blueprints.game_card import game_card_bp
from blueprints.seasons import seasons_bp
from blueprints.game_shootout import game_shootout_bp

def create_app():
    app = Flask(__name__)
    db_params = get_db_params("hockey-blast-radonly")
    db_url = f"postgresql://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_params['dbname']}"
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['BACKGROUND_IMAGE'] = 'default_background.jpg'
    app.config['ORG_NAME'] = 'Hockey Blast'
    db.init_app(app)
    
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
    
    @app.route('/')
    def index():
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
        daily_skater_games_played = db.session.query(OrgStatsDailySkater, Human).join(Human, OrgStatsDailySkater.human_id == Human.id).filter(OrgStatsDailySkater.org_id == org_id).order_by(OrgStatsDailySkater.games_played.desc()).limit(top_n).all()
        daily_skater_goals = db.session.query(OrgStatsDailySkater, Human).join(Human, OrgStatsDailySkater.human_id == Human.id).filter(OrgStatsDailySkater.org_id == org_id).order_by(OrgStatsDailySkater.goals.desc()).limit(top_n).all()
        daily_skater_assists = db.session.query(OrgStatsDailySkater, Human).join(Human, OrgStatsDailySkater.human_id == Human.id).filter(OrgStatsDailySkater.org_id == org_id).order_by(OrgStatsDailySkater.assists.desc()).limit(top_n).all()
        daily_skater_points = db.session.query(OrgStatsDailySkater, Human).join(Human, OrgStatsDailySkater.human_id == Human.id).filter(OrgStatsDailySkater.org_id == org_id).order_by(OrgStatsDailySkater.points.desc()).limit(top_n).all()
        daily_skater_penalties = db.session.query(OrgStatsDailySkater, Human).join(Human, OrgStatsDailySkater.human_id == Human.id).filter(OrgStatsDailySkater.org_id == org_id).order_by(OrgStatsDailySkater.penalties.desc()).limit(top_n).all()

        daily_goalie_games_played = db.session.query(OrgStatsDailyGoalie, Human).join(Human, OrgStatsDailyGoalie.human_id == Human.id).filter(OrgStatsDailyGoalie.org_id == org_id).order_by(OrgStatsDailyGoalie.games_played.desc()).limit(top_n).all()
        daily_goalie_save_percentage = db.session.query(OrgStatsDailyGoalie, Human).join(Human, OrgStatsDailyGoalie.human_id == Human.id).filter(OrgStatsDailyGoalie.org_id == org_id).order_by(OrgStatsDailyGoalie.save_percentage.desc()).limit(top_n).all()

        daily_referee_games_reffed = db.session.query(OrgStatsDailyReferee, Human).join(Human, OrgStatsDailyReferee.human_id == Human.id).filter(OrgStatsDailyReferee.org_id == org_id).order_by(OrgStatsDailyReferee.games_reffed.desc()).limit(top_n).all()
        daily_referee_penalties_given = db.session.query(OrgStatsDailyReferee, Human).join(Human, OrgStatsDailyReferee.human_id == Human.id).filter(OrgStatsDailyReferee.org_id == org_id).order_by(OrgStatsDailyReferee.penalties_given.desc()).limit(top_n).all()
        daily_referee_gm_given = db.session.query(OrgStatsDailyReferee, Human).join(Human, OrgStatsDailyReferee.human_id == Human.id).filter(OrgStatsDailyReferee.org_id == org_id).order_by(OrgStatsDailyReferee.gm_given.desc()).limit(top_n).all()
        
        return render_template('index.html', games_indexed=games_indexed, last_scheduled=last_scheduled, last_scheduled_time=last_scheduled_time, last_played=last_played, last_played_time=last_played_time, background_image=app.config['BACKGROUND_IMAGE'], 
                               daily_skater_games_played=daily_skater_games_played, daily_skater_goals=daily_skater_goals, daily_skater_assists=daily_skater_assists, daily_skater_points=daily_skater_points, daily_skater_penalties=daily_skater_penalties,
                               daily_goalie_games_played=daily_goalie_games_played, daily_goalie_save_percentage=daily_goalie_save_percentage,
                               daily_referee_games_reffed=daily_referee_games_reffed, daily_referee_penalties_given=daily_referee_penalties_given, daily_referee_gm_given=daily_referee_gm_given, org_name = organization.organization_name)

    @app.route('/special_stats')
    def special_stats():
        # Your logic to get any data needed for special_stats.html
        return render_template('special_stats.html', background_image=app.config['BACKGROUND_IMAGE'])

    return app

def run_http(app, port):
    app.run(host='0.0.0.0', port=port)  # HTTP on specified port

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()  # Create database tables for all models
    Thread(target=run_http, args=(app, 5000)).start()