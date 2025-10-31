import pandas as pd
from flask import Blueprint, jsonify, render_template, request
from hockey_blast_common_lib.models import (Division, Game, LevelsMonthly,
                                            Season, db)

day_of_week_bp = Blueprint("day_of_week", __name__)


@day_of_week_bp.route("/day_of_week")
def interactive_plot():
    levels = db.session.query(LevelsMonthly.level).distinct().all()
    levels = sorted([level[0] for level in levels])  # Sort levels alphabetically
    return render_template("day_of_week.html", levels=levels)


@day_of_week_bp.route("/get_day_of_week_data", methods=["POST"])
def get_day_of_week_data():
    x_axis = request.json.get("x_axis")
    plot_level = request.json.get("plot_level")
    print(f"Debug: X Axis: {x_axis}, Plot Level: {plot_level}")

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
                .group_by(
                    db.cast(db.extract("year", Game.date), db.Integer),
                    db.cast(db.extract("month", Game.date), db.Integer),
                    Game.day_of_week,
                )
            )
            if plot_level != "all":
                query = query.filter(Division.level == plot_level)
        else:
            query = (
                db.session.query(
                    Season.season_number,
                    Season.season_name,
                    Game.day_of_week,
                    db.func.count(Game.id).label("games_count"),
                )
                .join(Division, Game.division_id == Division.id)
                .join(Season, Division.season_number == Season.season_number)
                .group_by(Season.season_number, Season.season_name, Game.day_of_week)
            )
            if plot_level != "all":
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
        df = df.sort_values("season_number")
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
