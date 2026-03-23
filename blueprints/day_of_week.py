import pandas as pd
from flask import Blueprint, jsonify, render_template, request
from hockey_blast_common_lib.models import (Division, Game, League,
                                            LevelsMonthly, Organization,
                                            Season, db)

day_of_week_bp = Blueprint("day_of_week", __name__)


@day_of_week_bp.route("/day_of_week")
def interactive_plot():
    # Pass orgs and leagues so the dropdowns can be populated client-side
    organizations = db.session.query(Organization).order_by(Organization.organization_name).all()
    return render_template("day_of_week.html", organizations=organizations)


@day_of_week_bp.route("/get_day_of_week_leagues", methods=["POST"])
def get_day_of_week_leagues():
    org_id = request.json.get("org_id")
    try:
        org_id = int(org_id) if org_id else None
    except (ValueError, TypeError):
        return jsonify([])

    query = db.session.query(League).order_by(League.league_name)
    if org_id:
        query = query.filter(League.org_id == org_id)
    leagues = query.all()
    return jsonify([{"id": l.id, "league_name": l.league_name} for l in leagues])


@day_of_week_bp.route("/get_day_of_week_levels", methods=["POST"])
def get_day_of_week_levels():
    org_id = request.json.get("org_id")
    league_id = request.json.get("league_id")
    try:
        org_id = int(org_id) if org_id else None
        league_id = int(league_id) if league_id else None
    except (ValueError, TypeError):
        return jsonify([])

    # Get distinct level strings scoped to org/league
    query = db.session.query(Division.level).distinct().join(
        Season, Division.season_id == Season.id
    )
    if league_id:
        query = query.filter(Season.league_id == league_id)
    elif org_id:
        query = query.filter(Division.org_id == org_id)

    levels = sorted([row[0] for row in query.all() if row[0]])
    return jsonify(levels)


@day_of_week_bp.route("/get_day_of_week_data", methods=["POST"])
def get_day_of_week_data():
    x_axis = request.json.get("x_axis")
    plot_level = request.json.get("plot_level")
    league_id = request.json.get("league_id")
    org_id = request.json.get("org_id")

    try:
        league_id = int(league_id) if league_id else None
        org_id = int(org_id) if org_id else None
    except (ValueError, TypeError):
        league_id = None
        org_id = None

    def get_query():
        if x_axis == "year_month":
            query = (
                db.session.query(
                    db.cast(db.extract("year", Game.date), db.Integer).label("year"),
                    db.cast(db.extract("month", Game.date), db.Integer).label("month"),
                    Game.day_of_week,
                    db.func.count(Game.id).label("games_count"),
                )
                .join(Division, Game.division_id == Division.id)
                .join(Season, Division.season_id == Season.id)
                .group_by(
                    db.cast(db.extract("year", Game.date), db.Integer),
                    db.cast(db.extract("month", Game.date), db.Integer),
                    Game.day_of_week,
                )
            )
            if league_id:
                query = query.filter(Season.league_id == league_id)
            elif org_id:
                query = query.filter(Division.org_id == org_id)
            if plot_level and plot_level != "all":
                query = query.filter(Division.level == plot_level)
        else:
            query = (
                db.session.query(
                    Season.id.label("season_id"),
                    Season.season_number,
                    Season.season_name,
                    Game.day_of_week,
                    db.func.count(Game.id).label("games_count"),
                )
                .join(Division, Game.division_id == Division.id)
                .join(Season, Division.season_id == Season.id)
                .group_by(Season.id, Season.season_number, Season.season_name, Game.day_of_week)
            )
            if league_id:
                query = query.filter(Season.league_id == league_id)
            elif org_id:
                query = query.filter(Division.org_id == org_id)
            if plot_level and plot_level != "all":
                query = query.filter(Division.level == plot_level)
        return query

    query = get_query()
    df = pd.read_sql(query.statement, db.engine)

    if df.empty:
        return jsonify({"x": [], "y": {}})

    if x_axis == "year_month":
        df["x"] = df["year"].astype(str) + "/" + df["month"].astype(str).str.zfill(2)
        df = df.sort_values("x")
    else:
        df = df.sort_values(["season_number", "season_id"])
        df["x"] = df["season_name"]

    days_of_week = {
        1: "Monday",
        2: "Tuesday",
        3: "Wednesday",
        4: "Thursday",
        5: "Friday",
        6: "Saturday",
        7: "Sunday",
    }
    result = {
        "x": df["x"].unique().tolist(),
        "y": {day_name: [] for day_name in days_of_week.values()},
    }

    for x_value in result["x"]:
        group_df = df[df["x"] == x_value]
        total_games = group_df["games_count"].sum()

        for day, day_name in days_of_week.items():
            day_games = group_df[group_df["day_of_week"] == day]["games_count"].sum()
            percentage = (day_games / total_games) if total_games > 0 else 0
            result["y"][day_name].append(percentage)

    return jsonify(result)
