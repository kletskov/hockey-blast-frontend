import json
import logging
import os
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from threading import Thread

import flask_table.columns
import flask_table.table
# Import kinde_flask to register the Flask framework - exactly like their example
import psycopg2
from dotenv import load_dotenv
from flask import (Flask, g, jsonify, redirect, render_template, request,
                   send_from_directory, session, url_for)
from flask_restx import Api
from hockey_blast_common_lib.db_connection import get_db_params
from hockey_blast_common_lib.models import (Game, Human, HumanAlias,
                                            Organization, RequestLog,
                                            Team, db)
from hockey_blast_common_lib.stats_models import (OrgStatsDailyGoalie,
                                                  OrgStatsDailyHuman,
                                                  OrgStatsDailyReferee,
                                                  OrgStatsDailySkater,
                                                  OrgStatsSkater,
                                                  OrgStatsWeeklyGoalie,
                                                  OrgStatsWeeklyHuman,
                                                  OrgStatsWeeklyReferee,
                                                  OrgStatsWeeklySkater)
from hockey_blast_common_lib.stats_utils import ALL_ORGS_ID
from hockey_blast_common_lib.utils import (get_fake_human_for_stats,
                                           get_non_human_ids)
from kinde_sdk.auth.oauth import OAuth
from markupsafe import Markup

from flask_session import Session
from options import MAX_HUMAN_SEARCH_RESULTS, MAX_TEAM_SEARCH_RESULTS

# Load environment variables
load_dotenv()
print("Loading environment variables from .env")

# Debug: Print the DB_HOST environment variable
flask_table.table.Markup = Markup
flask_table.columns.Markup = Markup

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

import ipaddress
import re

from api.v1.divisions import divisions_ns
from api.v1.organizations import organizations_ns
from api.v1.seasons import seasons_ns
from blueprints.about import about_bp
from blueprints.active_players import active_players_bp
from blueprints.ai_search import ai_search_bp
from blueprints.day_of_week import day_of_week_bp
from blueprints.days_of_week import days_of_week_bp
from blueprints.days_of_week_dropdowns import days_of_week_dropdowns_bp
from blueprints.dropdowns import dropdowns_bp
from blueprints.game_card import game_card_bp
from blueprints.game_shootout import game_shootout_bp
from blueprints.games import games_bp
from blueprints.goalie_performance import goalie_performance_bp
from blueprints.hall_of_fame import hall_of_fame_bp
from blueprints.human_stats import human_stats_bp
from blueprints.penalties import penalties_bp
from blueprints.players_per_season import players_per_season_bp
# from blueprints.rest_api import rest_api_bp
from blueprints.referee_performance import referee_performance_bp
from blueprints.request_logs import request_logs_bp
from blueprints.scorekeeper_performance import scorekeeper_performance_bp
from blueprints.scorekeeper_quality import scorekeeper_quality_bp
from blueprints.search_teams import search_teams_bp
from blueprints.seasons import seasons_bp
from blueprints.skater_performance import skater_performance_bp
from blueprints.skater_to_skater import skater_to_skater_bp  # Add this import
from blueprints.team_stats import team_stats_bp
from blueprints.teams_per_season import teams_per_season_bp
from blueprints.time_of_games import time_of_games_bp
from blueprints.two_skaters_selection import \
    two_skaters_selection_bp  # Add this import
from blueprints.version import version_bp

suspicious_subnets = [
    "185.6.233.0/24",
    "185.191.171.0/24",
    "185.220.101.0/24",
    "185.220.102.0/24",
    "185.220.103.0/24",
    "185.220.100.0/24",
    "91.219.212.0/24",
    "89.234.157.0/24",
    "45.9.20.0/22",
    "176.111.173.0/24",
    "176.59.0.0/16",
    "77.40.0.0/16",
]

suspicious_networks = [ipaddress.ip_network(subnet) for subnet in suspicious_subnets]


def is_suspicious_ip(ip: str) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip)
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_reserved
            or ip_obj.is_link_local
        ):
            return True
        for net in suspicious_networks:
            if ip_obj in net:
                return True
    except ValueError:
        return True
    return False


def is_obviously_junk_user_agent(user_agent: str) -> bool:
    if not user_agent:
        return True

    ua = user_agent.lower()

    # Red flags: ancient browsers, fake versions, scraping tools
    red_flags = [
        "windows 95",
        "windows 98",
        "windows nt 5.0",
        "windows nt 5.01",
        "windows nt 5.1",
        "windows ce",
        "windows nt 11.0",
        "msie 5.0",
        "msie 6.0",
        "msie 7.0",
        "msie 8.0",
        "opera/9.",
        "presto/2.",
        "samsungbrowser/3.",
        "ucbrowser",
        "baidubrowser",
        "phantomjs",
        "crawler",
        "spider",
        "httpclient",
        "wget",
        "curl",
    ]
    if any(flag in ua for flag in red_flags):
        return True

    # Nonsensical Gecko date stamps
    if re.search(r"gecko/\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+", ua):
        return True

    # Suspicious Android devices (often associated with botnets)
    suspicious_devices = [
        "sm-j700f",
        "sm-j701f",
        "redmi",
        "tecno",
        "itel",
        "lava",
        "infinix",
        "vivo",
        "nokia",
        "huawei",
        "moto e5",
    ]
    if any(dev in ua for dev in suspicious_devices):
        if "android 6" in ua or "android 7" in ua or "android 5" in ua:
            return True

    # iPhone with very old iOS but modern Chrome/Safari versions
    if "iphone" in ua and "os 10" in ua:
        if "chrome/114" in ua or "safari/604" in ua:
            return True

    # Safari on Windows (not legitimate)
    if "safari" in ua and "windows nt 10.0" in ua:
        return True

    # Repetitive spoofed versions
    if "chrome/114.0.5735.196" in ua:
        return True

    # Unknown or fake language codes
    fake_locales = ["kok-in", "brx-in", "sd-in", "ks-in", "gu-in"]
    if any(loc in ua for loc in fake_locales):
        return True

    # Safari without AppleWebKit
    if "safari" in ua and "applewebkit" not in ua:
        return True

    # Lack of common components
    if "mozilla/5.0" not in ua or not any(
        p in ua for p in ["applewebkit", "gecko/", "chrome/", "safari/", "edg/"]
    ):
        return True

    return False


def get_user_agent():
    return request.headers.get("User-Agent")


def get_client_ip():
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0]
    return request.remote_addr


def create_prod_app():
    """Create the application with production database."""
    return _create_app("frontend")


def create_sample_app():
    """Create the application with sample database."""
    return _create_app("frontend-sample-db")


def _create_app(db_name):
    """Internal function to create the app with the specified database."""
    app = Flask(__name__)

    # Check for debug mode from environment variable
    debug_mode = os.environ.get("DEBUG_MODE", "").lower() in ("true", "1", "yes", "on")

    # Configure app
    db_params = get_db_params(db_name)
    db_url = f"postgresql://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_params['dbname']}"
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["BACKGROUND_IMAGE"] = "default_background.jpg"
    app.config["ORG_NAME"] = "Hockey Blast"
    app.config["DEBUG"] = debug_mode
    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY", "your-secret-key-here-change-this-in-production"
    )

    # Critical session settings for HTTPS production deployment
    app.config["SESSION_TYPE"] = os.getenv("SESSION_TYPE", "filesystem")
    app.config["SESSION_PERMANENT"] = (
        os.getenv("SESSION_PERMANENT", "False").lower() == "true"
    )
    app.config["SESSION_USE_SIGNER"] = True
    app.config["SESSION_COOKIE_SECURE"] = (
        os.getenv("SESSION_COOKIE_SECURE", "True").lower() == "true"
    )  # Only send cookies over HTTPS
    app.config["SESSION_COOKIE_HTTPONLY"] = True  # Prevent JavaScript access

    # Fix SameSite value - ensure it's one of the valid values
    samesite_value = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    if samesite_value not in ["Strict", "Lax", "None"]:
        samesite_value = "Lax"  # Default to Lax if invalid
    app.config["SESSION_COOKIE_SAMESITE"] = samesite_value

    Session(app)

    # Set up more verbose logging in debug mode
    if debug_mode:
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
        logger.debug(f"Database URL: {db_url.replace(db_params['password'], '***')}")
        # Only enable SQLAlchemy query logging in debug mode
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    else:
        # In production, suppress SQLAlchemy INFO messages
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)

    db.init_app(app)

    # Initialize Kinde OAuth with Flask framework - exactly like their example
    kinde_oauth = OAuth(framework="flask", app=app)

    def get_authorized_data():
        """Get user data if authenticated - following Kinde example exactly"""
        if not kinde_oauth.is_authenticated():
            return None

        user = kinde_oauth.get_user_info()
        if not user:
            return None

        user_data = {
            "id": user.get("id"),
            "user_given_name": user.get("given_name"),
            "user_family_name": user.get("family_name"),
            "user_email": user.get("email"),
            "user_picture": user.get("picture"),
        }

        return user_data

    # Register blueprints
    app.register_blueprint(teams_per_season_bp)
    app.register_blueprint(human_stats_bp, url_prefix="/human_stats")
    app.register_blueprint(hall_of_fame_bp, url_prefix="/hall_of_fame")
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
    app.register_blueprint(games_bp, url_prefix="/games")
    app.register_blueprint(dropdowns_bp, url_prefix="/dropdowns")
    app.register_blueprint(about_bp)
    app.register_blueprint(ai_search_bp)
    app.register_blueprint(penalties_bp, url_prefix="/penalties")
    app.register_blueprint(skater_performance_bp, url_prefix="/skater_performance")
    app.register_blueprint(goalie_performance_bp, url_prefix="/goalie_performance")
    app.register_blueprint(request_logs_bp, url_prefix="/request_logs")
    app.register_blueprint(days_of_week_bp, url_prefix="/days_of_week")
    app.register_blueprint(days_of_week_dropdowns_bp, url_prefix="/days_of_week")
    app.register_blueprint(referee_performance_bp, url_prefix="/referee_performance")
    app.register_blueprint(
        scorekeeper_performance_bp, url_prefix="/scorekeeper_performance"
    )
    app.register_blueprint(scorekeeper_quality_bp, url_prefix="/scorekeeper_quality")
    app.register_blueprint(
        skater_to_skater_bp, url_prefix="/skater_to_skater"
    )  # Add this line
    app.register_blueprint(
        two_skaters_selection_bp, url_prefix="/two_skaters_selection"
    )  # Add this line
    # REST API blueprint (provides /swagger and /api/v1/* routes)
    # app.register_blueprint(rest_api_bp)

    @app.before_request
    def before_request():
        # Record start time for response time calculation
        g.start_time = time.time()

        if request.path in [
            "/favicon.ico",
            "/dropdowns",
            "/dropdowns/filter_levels",
            "/dropdowns/filter_seasons",
            "/games/filter_games",
        ]:
            g.skip_logging = True
            return

        user_agent = request.headers.get("User-Agent")
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)

        # Exempt /ai-search from bot detection (testing endpoint)
        if request.path != "/ai-search" and is_obviously_junk_user_agent(user_agent):
            logger.warning(f"JUNK USER-AGENT: {user_agent} from {client_ip}")
            g.skip_logging = True
            return "", 204  # Silently drop or use 403 to block

        # Store request data in g for logging in after_request
        g.skip_logging = False
        g.user_agent = user_agent
        g.client_ip = client_ip
        g.path = request.path
        g.cgi_params = request.query_string.decode("utf-8")
        pst = timezone(timedelta(hours=-8))
        g.timestamp = datetime.now(pst)

    @app.after_request
    def after_request(response):
        # Calculate response time
        if hasattr(g, "start_time"):
            response_time_ms = (
                time.time() - g.start_time
            ) * 1000  # Convert to milliseconds
        else:
            response_time_ms = None

        # Skip logging if flagged
        if getattr(g, "skip_logging", True):
            return response

        # Log the request with response time
        try:
            log_entry = RequestLog(
                user_agent=g.user_agent,
                client_ip=g.client_ip,
                path=g.path,
                timestamp=g.timestamp,
                cgi_params=g.cgi_params,
                response_time_ms=response_time_ms,
            )
            db.session.add(log_entry)
            db.session.commit()
        except psycopg2.errors.InsufficientPrivilege as e:
            db.session.rollback()
            logger.error(
                f"Failed to log request: {e}. User '{db_params['user']}' does not have permission to access the table."
            )
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to log request: {e}")

        return response

    @app.route("/", methods=["GET", "POST"])
    def index():
        try:
            top_n = request.args.get("top_n", default=10, type=int)

            # Redirect to include top_n in the URL if not present
            if "top_n" not in request.args:
                return redirect(url_for("index", top_n=top_n))

            # Check if user is authenticated - following Kinde example
            auth_data = get_authorized_data()

            # Fetch the latest date and time
            last_scheduled = (
                db.session.query(Game)
                .order_by(Game.date.desc(), Game.time.desc())
                .first()
            )
            last_played = (
                db.session.query(Game)
                .filter(Game.status.startswith("Final"))
                .order_by(Game.date.desc(), Game.time.desc())
                .first()
            )

            # Format the time as HH:MM AM/PM
            last_scheduled_time = (
                last_scheduled.time.strftime("%I:%M%p") if last_scheduled else None
            )
            last_played_time = (
                last_played.time.strftime("%I:%M%p") if last_played else None
            )

            # Get the fake human ID to exclude from scorekeeper stats
            fake_human_id = get_fake_human_for_stats(db.session)

            # Fetch top performers for the last day
            daily_skater_points = (
                db.session.query(OrgStatsDailySkater, Human, Organization)
                .join(Human, OrgStatsDailySkater.human_id == Human.id)
                .join(Organization, OrgStatsDailySkater.org_id == Organization.id)
                .filter(
                    OrgStatsDailySkater.points > 0,
                    OrgStatsDailySkater.org_id != ALL_ORGS_ID,
                )
                .order_by(OrgStatsDailySkater.points.desc())
                .limit(top_n)
                .all()
            )
            daily_goalie_games_played = (
                db.session.query(OrgStatsDailyGoalie, Human, Organization)
                .join(Human, OrgStatsDailyGoalie.human_id == Human.id)
                .join(Organization, OrgStatsDailyGoalie.org_id == Organization.id)
                .filter(
                    OrgStatsDailyGoalie.games_participated > 0,
                    OrgStatsDailyGoalie.org_id != ALL_ORGS_ID,
                )
                .order_by(
                    OrgStatsDailyGoalie.games_participated.desc(),
                    OrgStatsDailyGoalie.save_percentage.desc(),
                )
                .limit(top_n)
                .all()
            )
            daily_referee_games_reffed = (
                db.session.query(OrgStatsDailyReferee, Human, Organization)
                .join(Human, OrgStatsDailyReferee.human_id == Human.id)
                .join(Organization, OrgStatsDailyReferee.org_id == Organization.id)
                .filter(
                    OrgStatsDailyReferee.games_participated > 0,
                    OrgStatsDailyReferee.org_id != ALL_ORGS_ID,
                )
                .order_by(
                    OrgStatsDailyReferee.games_participated.desc(),
                    (
                        OrgStatsDailyReferee.gm_given
                        + OrgStatsDailyReferee.penalties_given
                    ).desc(),
                )
                .limit(top_n)
                .all()
            )
            daily_scorekeeper_games = (
                db.session.query(OrgStatsDailyHuman, Human, Organization)
                .join(Human, OrgStatsDailyHuman.human_id == Human.id)
                .join(Organization, OrgStatsDailyHuman.org_id == Organization.id)
                .filter(
                    OrgStatsDailyHuman.games_scorekeeper > 0,
                    OrgStatsDailyHuman.human_id != fake_human_id,
                    OrgStatsDailyHuman.org_id != ALL_ORGS_ID,
                )
                .order_by(OrgStatsDailyHuman.games_scorekeeper.desc())
                .limit(top_n)
                .all()
            )

            # Fetch top performers for the last week
            weekly_skater_points = (
                db.session.query(OrgStatsWeeklySkater, Human, Organization)
                .join(Human, OrgStatsWeeklySkater.human_id == Human.id)
                .join(Organization, OrgStatsWeeklySkater.org_id == Organization.id)
                .filter(
                    OrgStatsWeeklySkater.points > 0,
                    OrgStatsWeeklySkater.org_id != ALL_ORGS_ID,
                )
                .order_by(OrgStatsWeeklySkater.points.desc())
                .limit(top_n)
                .all()
            )
            weekly_goalie_games_played = (
                db.session.query(OrgStatsWeeklyGoalie, Human, Organization)
                .join(Human, OrgStatsWeeklyGoalie.human_id == Human.id)
                .join(Organization, OrgStatsWeeklyGoalie.org_id == Organization.id)
                .filter(
                    OrgStatsWeeklyGoalie.games_participated > 0,
                    OrgStatsWeeklyGoalie.org_id != ALL_ORGS_ID,
                )
                .order_by(
                    OrgStatsWeeklyGoalie.games_participated.desc(),
                    OrgStatsWeeklyGoalie.save_percentage.desc(),
                )
                .limit(top_n)
                .all()
            )
            weekly_referee_games_reffed = (
                db.session.query(OrgStatsWeeklyReferee, Human, Organization)
                .join(Human, OrgStatsWeeklyReferee.human_id == Human.id)
                .join(Organization, OrgStatsWeeklyReferee.org_id == Organization.id)
                .filter(
                    OrgStatsWeeklyReferee.games_participated > 0,
                    OrgStatsWeeklyReferee.org_id != ALL_ORGS_ID,
                )
                .order_by(
                    OrgStatsWeeklyReferee.games_participated.desc(),
                    (
                        OrgStatsWeeklyReferee.gm_given
                        + OrgStatsWeeklyReferee.penalties_given
                    ).desc(),
                )
                .limit(top_n)
                .all()
            )
            weekly_scorekeeper_games = (
                db.session.query(OrgStatsWeeklyHuman, Human, Organization)
                .join(Human, OrgStatsWeeklyHuman.human_id == Human.id)
                .join(Organization, OrgStatsWeeklyHuman.org_id == Organization.id)
                .filter(
                    OrgStatsWeeklyHuman.games_scorekeeper > 0,
                    OrgStatsWeeklyHuman.human_id != fake_human_id,
                    OrgStatsWeeklyHuman.org_id != ALL_ORGS_ID,
                )
                .order_by(OrgStatsWeeklyHuman.games_scorekeeper.desc())
                .limit(top_n)
                .all()
            )

            # Fetch top current point streak performers (all-time stats) - only show if last game within 1 month
            one_month_ago = datetime.now() - timedelta(days=30)
            current_point_streak_skaters = (
                db.session.query(OrgStatsSkater, Human, Organization)
                .join(Human, OrgStatsSkater.human_id == Human.id)
                .join(Organization, OrgStatsSkater.org_id == Organization.id)
                .join(Game, OrgStatsSkater.last_game_id == Game.id)
                .filter(
                    OrgStatsSkater.current_point_streak > 0,
                    OrgStatsSkater.org_id != ALL_ORGS_ID,
                    Game.date >= one_month_ago,
                )
                .order_by(
                    OrgStatsSkater.current_point_streak.desc(),
                    OrgStatsSkater.current_point_streak_avg_points.desc(),
                )
                .limit(top_n)
                .all()
            )

            # Fetch latest completed game per organization

            latest_completed_games = []
            organizations = (
                db.session.query(Organization)
                .filter(Organization.id != ALL_ORGS_ID)
                .all()
            )
            day_of_week_map = {
                1: "Mon",
                2: "Tue",
                3: "Wed",
                4: "Thu",
                5: "Fri",
                6: "Sat",
                7: "Sun",
            }

            for org in organizations:
                latest_game = (
                    db.session.query(Game)
                    .filter(Game.org_id == org.id, Game.status.startswith("Final"))
                    .order_by(Game.date.desc(), Game.time.desc())
                    .first()
                )

                if latest_game:
                    day_of_week = day_of_week_map.get(latest_game.day_of_week, "")
                    date_time_str = f"{day_of_week} {latest_game.date.strftime('%m/%d/%y')} {latest_game.time.strftime('%I:%M%p')}"
                    latest_completed_games.append(
                        {
                            "org_name": org.organization_name,
                            "game_id": latest_game.id,
                            "date_time": date_time_str,
                        }
                    )

            if request.method == "POST":
                team_name = request.form.get("team_name")
                query = db.session.query(Team)

                if team_name:
                    query = query.filter(Team.name.ilike(f"%{team_name}%"))

                    # Apply limit directly in the query
                    results = query.limit(MAX_TEAM_SEARCH_RESULTS).all()

                    if not results:
                        return render_template(
                            "search_teams.html",
                            no_results=True,
                            max_results=MAX_TEAM_SEARCH_RESULTS,
                        )

                    # If only one result, redirect directly to that team's page
                    if len(results) == 1:
                        return redirect(url_for("team_stats.team_stats", team_id=results[0].id))

                    links = []
                    for team in results:
                        link_text = team.name
                        encoded_link_text = urllib.parse.quote(link_text)
                        link = f'<a href="{url_for("team_stats.team_stats", team_id=team.id)}">{link_text}</a>'
                        links.append(link)
                else:
                    first_name = request.form.get("first_name")
                    last_name = request.form.get("last_name")

                    # Get non-human IDs to filter out
                    non_human_ids = get_non_human_ids(db.session)

                    query = db.session.query(Human)

                    if first_name:
                        query = query.filter(Human.first_name.ilike(f"%{first_name}%"))
                    if last_name:
                        query = query.filter(Human.last_name.ilike(f"%{last_name}%"))

                    # Filter out non-human entities
                    if non_human_ids:
                        query = query.filter(~Human.id.in_(non_human_ids))

                    # Apply limit directly in the query
                    results = query.limit(MAX_HUMAN_SEARCH_RESULTS).all()

                    # If only one result, redirect directly to that human's page
                    if len(results) == 1:
                        return redirect(url_for("human_stats.human_stats", human_id=results[0].id, top_n=20))

                    links = []
                    for player in results:
                        aliases = (
                            db.session.query(HumanAlias)
                            .filter(HumanAlias.human_id == player.id)
                            .all()
                        )
                        alias_names = [
                            f"{alias.first_name} {alias.middle_name} {alias.last_name}".strip()
                            for alias in aliases
                            if f"{alias.first_name} {alias.middle_name} {alias.last_name}".strip()
                            != f"{player.first_name} {player.middle_name} {player.last_name}".strip()
                        ]
                        alias_text = (
                            f" A.K.A. {', '.join(alias_names)}" if alias_names else ""
                        )
                        link_text = f"{player.first_name} {player.middle_name} {player.last_name}{alias_text}"
                        link = f'<a href="{url_for("human_stats.human_stats", human_id=player.id, top_n=20)}">{link_text}</a>'
                        links.append(link)

                return render_template(
                    "index.html",
                    search_results=links,
                    auth_data=auth_data,
                    last_scheduled=last_scheduled,
                    last_scheduled_time=last_scheduled_time,
                    last_played=last_played,
                    last_played_time=last_played_time,
                    daily_skater_points=daily_skater_points,
                    daily_goalie_games_played=daily_goalie_games_played,
                    daily_referee_games_reffed=daily_referee_games_reffed,
                    daily_scorekeeper_games=daily_scorekeeper_games,
                    weekly_skater_points=weekly_skater_points,
                    weekly_goalie_games_played=weekly_goalie_games_played,
                    weekly_referee_games_reffed=weekly_referee_games_reffed,
                    weekly_scorekeeper_games=weekly_scorekeeper_games,
                    current_point_streak_skaters=current_point_streak_skaters,
                    latest_completed_games=latest_completed_games,
                )
            return render_template(
                "index.html",
                search_results=None,
                auth_data=auth_data,
                last_scheduled=last_scheduled,
                last_scheduled_time=last_scheduled_time,
                last_played=last_played,
                last_played_time=last_played_time,
                daily_skater_points=daily_skater_points,
                daily_goalie_games_played=daily_goalie_games_played,
                daily_referee_games_reffed=daily_referee_games_reffed,
                daily_scorekeeper_games=daily_scorekeeper_games,
                weekly_skater_points=weekly_skater_points,
                weekly_goalie_games_played=weekly_goalie_games_played,
                weekly_referee_games_reffed=weekly_referee_games_reffed,
                weekly_scorekeeper_games=weekly_scorekeeper_games,
                current_point_streak_skaters=current_point_streak_skaters,
                latest_completed_games=latest_completed_games,
            )
        except Exception as e:
            error_info = {
                "error": str(e),
                "db_params": {**db_params, "password": "HIDDEN"},
            }
            return render_template("error.html", error_info=error_info)

    @app.route("/auth/status")
    def auth_status():
        """Show authentication status - for testing"""
        auth_data = get_authorized_data()
        is_authenticated = kinde_oauth.is_authenticated()

        return jsonify(
            {
                "is_authenticated": is_authenticated,
                "auth_data": auth_data,
                "message": (
                    "Authentication working!"
                    if is_authenticated
                    else "Not authenticated"
                ),
            }
        )

    @app.route("/session")
    def session_info():
        """Show detailed session information"""
        auth_data = get_authorized_data()
        is_authenticated = kinde_oauth.is_authenticated()

        # Get Flask session data (be careful not to expose sensitive info)
        session_data = {}
        for key in session.keys():
            # Don't expose sensitive session data
            if key not in ["_permanent", "_fresh"]:
                session_data[key] = (
                    str(session[key])[:100] + "..."
                    if len(str(session[key])) > 100
                    else session[key]
                )

        return jsonify(
            {
                "is_authenticated": is_authenticated,
                "auth_data": auth_data,
                "session_keys": list(session.keys()),
                "session_data": session_data,
                "message": "Session info retrieved successfully",
            }
        )

    @app.route("/special_stats")
    def special_stats():
        return render_template(
            "special_stats.html", background_image=app.config["BACKGROUND_IMAGE"]
        )

    @app.route("/robots.txt")
    def robots_txt():
        return send_from_directory(app.root_path, "robots.txt")

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(app.root_path, "favicon.ico")

    @app.route("/about")
    def about():
        return render_template("about.html")

    api = Api(
        app,
        version="1.0",
        title="Hockey BLAST API",
        description="RESTful API",
        doc="/swagger",
    )

    api.add_namespace(organizations_ns, path="/api/v1")
    api.add_namespace(divisions_ns, path="/api/v1")
    api.add_namespace(seasons_ns, path="/api/v1")

    def json_safe_dict(d):
        """Convert a dictionary to a JSON-safe format."""
        result = {}
        for k, v in d.items():
            if isinstance(v, timedelta):
                # Convert timedelta to string representation
                days = v.days
                hours, remainder = divmod(v.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                result[k] = f"{days}d {hours}h {minutes}m {seconds}s"
            elif isinstance(v, dict):
                # Recursively process nested dictionaries
                result[k] = json_safe_dict(v)
            elif hasattr(v, "__dict__"):
                # Handle objects by getting their __dict__
                try:
                    result[k] = str(v)
                except:
                    result[k] = "Not serializable"
            else:
                # Try to use the value as is, if it fails, convert to string
                try:
                    # Check if it's JSON serializable
                    json.dumps(v)
                    result[k] = v
                except (TypeError, OverflowError):
                    result[k] = str(v)
        return result

    @app.route("/debug")
    def debug_info():
        """Endpoint to display debug information."""
        if not debug_mode:
            return "Debug mode not enabled. Set DEBUG_MODE=true to see details.", 403

        # Get safe environment variables (exclude sensitive info)
        safe_env_vars = {}
        for k, v in os.environ.items():
            if not any(s in k.lower() for s in ["key", "secret", "password", "token"]):
                safe_env_vars[k] = v

        # Get a list of all registered routes
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(
                {
                    "endpoint": rule.endpoint,
                    "methods": sorted(
                        [m for m in rule.methods if m not in ("HEAD", "OPTIONS")]
                    ),
                    "path": rule.rule,
                }
            )

        # Get database connection status
        try:
            with db.engine.connect() as conn:
                db_status = "Connected"
        except Exception as e:
            db_status = f"Error: {str(e)}"

        # Make app config JSON-safe
        safe_config = json_safe_dict(
            {
                k: v
                for k, v in app.config.items()
                if not any(
                    s in k.lower() for s in ["key", "secret", "password", "token"]
                )
            }
        )

        debug_data = {
            "app_config": safe_config,
            "environment": safe_env_vars,
            "routes": routes,
            "db_status": db_status,
            "registered_blueprints": list(app.blueprints.keys()),
        }

        return jsonify(debug_data)

    @app.route("/test-error")
    def test_error():
        """Endpoint to test error handling."""
        if not debug_mode:
            return "Debug mode not enabled. Set DEBUG_MODE=true to test errors.", 403

        # Raise a test exception
        raise Exception("This is a test error to check error handling")

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"500 error: {str(e)}")
        if debug_mode:
            # In debug mode, return detailed error information
            import traceback

            # Get traceback info
            error_traceback = traceback.format_exc()
            # Get safe database params (hide password)
            safe_db_params = {
                k: (v if k != "password" else "***") for k, v in db_params.items()
            }

            # Return JSON with error details
            response = jsonify(
                {
                    "error": str(e),
                    "traceback": error_traceback,
                    "db_params": safe_db_params,
                    "debug_mode": debug_mode,
                }
            )
            response.status_code = 500
            return response
        else:
            # In production, return a simple error page
            return (
                render_template(
                    "error.html", error_info={"error": "Internal Server Error"}
                ),
                500,
            )

    @app.errorhandler(Exception)
    def handle_exception(e):
        # Don't handle 404s and other HTTP exceptions in the global handler
        if hasattr(e, "code") and e.code == 404:
            return e

        app.logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        if debug_mode:
            # In debug mode, return detailed error information
            import traceback

            # Get traceback info
            error_traceback = traceback.format_exc()
            # Get safe database params (hide password)
            safe_db_params = {
                k: (v if k != "password" else "***") for k, v in db_params.items()
            }

            # Return JSON with error details
            response = jsonify(
                {
                    "error": str(e),
                    "error_type": e.__class__.__name__,
                    "traceback": error_traceback,
                    "db_params": safe_db_params,
                    "debug_mode": debug_mode,
                }
            )
            response.status_code = 500
            return response
        else:
            # In production, return a simple error page
            return (
                render_template(
                    "error.html", error_info={"error": "An unexpected error occurred"}
                ),
                500,
            )

    return app


def run_app(app, port):
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    app1 = create_prod_app()
    thread1 = Thread(target=run_app, args=(app1, 5001))
    thread1.start()
    thread1.join()

    # app2 = create_sample_app()
    # thread2 = Thread(target=run_app, args=(app2, 5005))
    # thread2.start()
    # thread2.join()
