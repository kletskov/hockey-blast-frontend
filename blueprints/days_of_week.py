from flask import Blueprint, current_app, jsonify, render_template, request
from hockey_blast_common_lib.models import (Division, Game, Level,
                                            Organization, Season, db)
from hockey_blast_common_lib.stats_utils import ALL_ORGS_ID
from sqlalchemy import func

days_of_week_bp = Blueprint("days_of_week", __name__, template_folder="../templates")


@days_of_week_bp.route("/", methods=["GET"])
def index():
    org_id = request.args.get("org_id", type=int)
    organizations = (
        db.session.query(Organization).order_by(Organization.organization_name).all()
    )

    all_orgs_option = Organization(
        id=ALL_ORGS_ID, organization_name="All Organizations"
    )
    organizations_with_all = [all_orgs_option] + organizations

    selected_org_id_actual = org_id
    if org_id is None and organizations:
        selected_org_id_actual = organizations[0].id
    elif org_id == ALL_ORGS_ID:
        selected_org_id_actual = ALL_ORGS_ID

    return render_template(
        "days_of_week.html",
        organizations=organizations_with_all,
        selected_org_id=selected_org_id_actual,
        ALL_ORGS_ID=ALL_ORGS_ID,
    )


@days_of_week_bp.route("/filter_days", methods=["POST"])
def filter_days():
    try:
        data = request.get_json()
        org_id = data.get("org_id")
        level_id = data.get("level_id")
        season_id = data.get("season_id")

        # Robust parsing
        try:
            org_id = (
                int(org_id) if org_id and org_id != "null" and org_id != "" else None
            )
            level_id = (
                int(level_id)
                if level_id and level_id != "null" and level_id != ""
                else None
            )
            season_id = (
                int(season_id)
                if season_id and season_id != "null" and season_id != ""
                else None
            )
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid filter ID"}), 400

        days_map = {
            1: "Monday",
            2: "Tuesday",
            3: "Wednesday",
            4: "Thursday",
            5: "Friday",
            6: "Saturday",
            7: "Sunday",
        }
        chart_order_days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        if level_id is not None:
            # Break down by seasons
            rows = []
            season_query = (
                db.session.query(Season)
                .filter(Season.org_id == org_id)
                .order_by(Season.season_number.desc())
            )
            seasons = season_query.all()
            for season in seasons:
                season_row = {day: 0 for day in chart_order_days}
                query = db.session.query(
                    Game.day_of_week, func.count(Game.id).label("game_count")
                ).join(Division, Game.division_id == Division.id)
                query = query.filter(
                    Division.level_id == level_id, Division.season_id == season.id
                )
                results = query.group_by(Game.day_of_week).all()
                for r in results:
                    day_name = days_map.get(r.day_of_week)
                    if day_name:
                        season_row[day_name] = r.game_count
                # Only add rows with non-zero data
                if any(season_row[day] > 0 for day in chart_order_days):
                    rows.append(
                        {
                            "label": season.season_name,
                            "data": [season_row[day] for day in chart_order_days],
                        }
                    )

            return jsonify({"header": chart_order_days, "rows": rows})
        else:
            # Filter levels to match dropdowns filtering logic
            query = (
                db.session.query(Level)
                .filter(
                    Level.org_id == org_id, Level.level_name.ilike("Adult Division%")
                )
                .order_by(Level.level_name.asc())
            )
            levels = query.all()

            # Calculate total games row
            total_games_row = {day: 0 for day in chart_order_days}
            rows = []
            for level in levels:
                level_name = level.level_name
                query = db.session.query(
                    Game.day_of_week, func.count(Game.id).label("game_count")
                ).join(Division, Game.division_id == Division.id)
                query = query.filter(Division.level_id == level.id)
                if season_id:
                    query = query.filter(Division.season_id == season_id)
                results = query.group_by(Game.day_of_week).all()
                row = {day: 0 for day in chart_order_days}
                for r in results:
                    day_name = days_map.get(r.day_of_week)
                    if day_name:
                        row[day_name] = r.game_count
                        total_games_row[day_name] += r.game_count
                rows.append(
                    {
                        "label": level_name,
                        "data": [row[day] for day in chart_order_days],
                    }
                )

            # Add total games row at the top
            rows.insert(
                0,
                {
                    "label": "Total Games",
                    "data": [total_games_row[day] for day in chart_order_days],
                },
            )

            return jsonify({"header": chart_order_days, "rows": rows})
    except Exception as e:
        current_app.logger.error(f"Error in /filter_days: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500
