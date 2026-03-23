from flask import Blueprint, current_app, jsonify, render_template, request
from hockey_blast_common_lib.models import (Division, Game, League, Level,
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
        league_id = data.get("league_id")
        level_id = data.get("level_id")
        season_id = data.get("season_id")

        # Robust parsing
        def _int(v):
            try:
                return int(v) if v and v != "null" and v != "" else None
            except (ValueError, TypeError):
                return None

        org_id = _int(org_id)
        league_id = _int(league_id)
        level_id = _int(level_id)
        season_id = _int(season_id)

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
            # Break down by seasons — scoped to league if provided
            rows = []
            season_query = db.session.query(Season).filter(Season.org_id == org_id)
            if league_id:
                season_query = season_query.filter(Season.league_id == league_id)
            seasons = season_query.order_by(Season.season_number.desc()).all()
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
            # Show levels for this league/season
            level_query = (
                db.session.query(Level)
                .filter(
                    Level.org_id == org_id, Level.level_name.ilike("Adult Division%")
                )
                .order_by(Level.level_name.asc())
            )
            # Restrict to levels that appear in divisions for this league/season
            div_level_query = db.session.query(Division.level_id).distinct()
            if season_id:
                div_level_query = div_level_query.filter(Division.season_id == season_id)
            elif league_id:
                div_level_query = div_level_query.join(
                    Season, Division.season_id == Season.id
                ).filter(Season.league_id == league_id)
            scoped_level_ids = [r[0] for r in div_level_query.all() if r[0]]
            if scoped_level_ids:
                level_query = level_query.filter(Level.id.in_(scoped_level_ids))

            levels = level_query.all()

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
                elif league_id:
                    query = query.join(
                        Season, Division.season_id == Season.id
                    ).filter(Season.league_id == league_id)
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
