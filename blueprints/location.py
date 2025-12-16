from datetime import date, datetime, timedelta
import sys
import os

# Add parent directory to path to import game_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from hockey_blast_common_lib.models import (Division, Game, Location, Team, db)
from jinja2 import Environment
from game_utils import is_game_live

location_bp = Blueprint("location", __name__)


@location_bp.route("/qr_location_redirect", methods=["GET"])
def qr_location_redirect():
    """QR code redirect endpoint for tracking scans separately from direct visits"""
    location_id = request.args.get("id")

    if not location_id:
        return "Missing location ID parameter", 400

    # Redirect to the main location endpoint
    return redirect(url_for("location.location", location_id=location_id))


@location_bp.route("/", methods=["GET"])
def location():
    location_id = request.args.get("location_id")

    # Get location details from database
    location_obj = None
    other_rinks = []

    if location_id:
        location_obj = db.session.query(Location).filter_by(id=location_id).first()

        # Define Sharks Ice San Jose rinks group (alphabetically sorted)
        sharks_ice_rinks = [
            {"id": 14, "name": "Black"},
            {"id": 8, "name": "Grey"},
            {"id": 18, "name": "Orange"},
            {"id": 1, "name": "Sharks"},
            {"id": 13, "name": "Tech CU"},
            {"id": 35, "name": "White"},
        ]

        # Check if current location is one of the Sharks Ice rinks
        sharks_ice_ids = [rink["id"] for rink in sharks_ice_rinks]
        if location_obj and int(location_id) in sharks_ice_ids:
            # Get other rinks (exclude current one)
            other_rinks = [
                rink for rink in sharks_ice_rinks
                if rink["id"] != int(location_id)
            ]

    return render_template(
        "location.html",
        location_id=location_id,
        location=location_obj,
        other_rinks=other_rinks,
    )


@location_bp.route("/filter_location_games", methods=["POST"])
def filter_location_games():
    location_id = request.json.get("location_id")

    if not location_id:
        return jsonify({"games": [], "error": "Location ID parameter required"}), 400

    # Calculate date range: 2 days before, today, and tomorrow
    today = date.today()
    two_days_ago = today - timedelta(days=2)
    tomorrow = today + timedelta(days=1)

    # Query games from 2 days before through tomorrow at this location
    query = db.session.query(Game, Location).join(Location, Game.location_id == Location.id)

    # Filter by location_id
    query = query.filter(Location.id == location_id)

    # Filter by date range (2 days before through tomorrow)
    query = query.filter(Game.date >= two_days_ago, Game.date <= tomorrow)

    # Order by date and time
    query = query.order_by(Game.date.asc(), Game.time.asc())

    results = query.all()

    games_data = []

    # Day of week mapping
    day_of_week_map = {
        1: "Mon",
        2: "Tue",
        3: "Wed",
        4: "Thu",
        5: "Fri",
        6: "Sat",
        7: "Sun",
    }

    # Calculate current time for highlighting games in progress
    now = datetime.now()

    # First pass: determine end times for each game based on next game starts
    # This is used for score display logic, not for orange highlighting
    game_end_times = {}
    for i in range(len(results)):
        game, location = results[i]
        if game.date and game.time:
            game_datetime = datetime.combine(game.date, game.time)

            # Default: 75 minutes after start (maximum game slot duration)
            game_end_estimate = game_datetime + timedelta(minutes=75)

            # Find the next game that starts at a DIFFERENT time (skip simultaneous games)
            for j in range(i + 1, len(results)):
                next_game, _ = results[j]
                if next_game.date and next_game.time:
                    next_game_datetime = datetime.combine(next_game.date, next_game.time)

                    # If next game starts at a different time, that marks the end of current game
                    # Allow small tolerance for "same start time" (simultaneous games on different rinks)
                    time_diff_minutes = (next_game_datetime - game_datetime).total_seconds() / 60
                    if time_diff_minutes > 5:  # Different start times - next game means previous ended
                        game_end_estimate = next_game_datetime
                        break  # Found the next different-time game, stop searching

            game_end_times[game.id] = game_end_estimate

    for game, location in results:
        if game.home_team_id is None or game.visitor_team_id is None:
            continue

        visitor_team = (
            db.session.query(Team).filter(Team.id == game.visitor_team_id).first()
        )
        home_team = db.session.query(Team).filter(Team.id == game.home_team_id).first()

        # Determine if game is currently live using shared utility function
        is_in_progress = is_game_live(game, now)

        # Format final score with bold for winner
        if game.status and game.status.lower().startswith("final"):
            home_period_scores = (
                (game.home_period_1_score or 0)
                + (game.home_period_2_score or 0)
                + (game.home_period_3_score or 0)
            )
            visitor_period_scores = (
                (game.visitor_period_1_score or 0)
                + (game.visitor_period_2_score or 0)
                + (game.visitor_period_3_score or 0)
            )

            # Determine winner and apply bold to winning score
            if game.visitor_final_score > game.home_final_score:
                final_score = f"<strong>{game.visitor_final_score}</strong> : {game.home_final_score}"
            elif game.home_final_score > game.visitor_final_score:
                final_score = f"{game.visitor_final_score} : <strong>{game.home_final_score}</strong>"
            else:
                # Tie - no bold
                final_score = f"{game.visitor_final_score} : {game.home_final_score}"
        elif is_in_progress:
            # Show live scores for in-progress games
            if game.status and game.status.upper() == "OPEN":
                # Game status is OPEN - show current score with (live) suffix
                # Sum period scores for live games (final_score is 0 during play)
                visitor_score = (
                    (game.visitor_period_1_score or 0)
                    + (game.visitor_period_2_score or 0)
                    + (game.visitor_period_3_score or 0)
                    + (game.visitor_ot_score or 0)
                )
                home_score = (
                    (game.home_period_1_score or 0)
                    + (game.home_period_2_score or 0)
                    + (game.home_period_3_score or 0)
                    + (game.home_ot_score or 0)
                )

                # Determine current leader and apply bold
                if visitor_score > home_score:
                    final_score = f"<strong>{visitor_score}</strong> : {home_score} (live)"
                elif home_score > visitor_score:
                    final_score = f"{visitor_score} : <strong>{home_score}</strong> (live)"
                else:
                    # Tied - no bold
                    final_score = f"{visitor_score} : {home_score} (live)"
            else:
                # Game is within time window but status is not OPEN - show "live"
                final_score = "live"
        else:
            # Game is not final and not in progress
            # Check if game time has passed - if so, show score instead of "Scheduled"
            if game.date and game.time:
                game_datetime = datetime.combine(game.date, game.time)
                if now > game_datetime:
                    # Game time has passed - show current score
                    visitor_score = (
                        (game.visitor_period_1_score or 0)
                        + (game.visitor_period_2_score or 0)
                        + (game.visitor_period_3_score or 0)
                        + (game.visitor_ot_score or 0)
                    )
                    home_score = (
                        (game.home_period_1_score or 0)
                        + (game.home_period_2_score or 0)
                        + (game.home_period_3_score or 0)
                        + (game.home_ot_score or 0)
                    )

                    # Show score even if 0-0 (game happened but no data yet)
                    if visitor_score > home_score:
                        final_score = f"<strong>{visitor_score}</strong> : {home_score}"
                    elif home_score > visitor_score:
                        final_score = f"{visitor_score} : <strong>{home_score}</strong>"
                    else:
                        # Tied or no score data yet
                        final_score = f"{visitor_score} : {home_score}"
                else:
                    # Game is in the future - show status
                    final_score = game.status or "Scheduled"
            else:
                final_score = game.status or "Scheduled"

        # Format team names with black "at" text
        team_names = f"<a href='{url_for('team_stats.team_stats', team_id=visitor_team.id)}'>{visitor_team.name}</a> <span style='color:black;'>at</span> <a href='{url_for('team_stats.team_stats', team_id=home_team.id)}'>{home_team.name}</a>"

        # Format date and time
        day_of_week = day_of_week_map.get(game.day_of_week, "")
        date_time = f"{day_of_week} {game.date.strftime('%m/%d/%y')} {game.time.strftime('%I:%M%p')}"

        games_data.append(
            {
                "id": game.id,
                "date": date_time,
                "time": game.time.strftime("%I:%M%p"),
                "final_score": final_score,
                "team_names": team_names,
                "status": game.status,
                "is_in_progress": is_in_progress,
            }
        )

    return jsonify({"games": games_data})


@location_bp.route("/rinks", methods=["GET"])
def rinks():
    # Get all locations from database
    locations = db.session.query(Location).all()

    # Helper function to get location display text for sorting
    def get_location_text(location):
        if location.location_name or location.rink_name:
            text = location.location_name or ""
            if location.rink_name:
                text += f", {location.rink_name} Rink"
            return text
        else:
            return location.location_in_game_source

    # Sort locations alphabetically by display text
    sorted_locations = sorted(locations, key=get_location_text)

    return render_template("rinks.html", locations=sorted_locations)
