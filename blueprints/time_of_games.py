import pandas as pd
from flask import Blueprint, jsonify, render_template, request
from hockey_blast_common_lib.models import Division, Game, Season, Team, db

time_of_games_bp = Blueprint("time_of_games", __name__)


@time_of_games_bp.route("/time_of_games")
def interactive_plot():
    levels = db.session.query(Division.level).distinct().all()
    levels = sorted([level[0] for level in levels])  # Sort levels alphabetically
    return render_template("time_of_games.html", levels=levels)


@time_of_games_bp.route("/get_time_of_games_data", methods=["POST"])
def get_time_of_games_data():
    plot_type = request.json.get("plot_type")
    level_1 = request.json.get("level_1")
    level_2 = request.json.get("level_2")
    plot_level = request.json.get("plot_level")
    print(
        f"Debug: Plot Type: {plot_type}, Level 1: {level_1}, Level 2: {level_2}, Plot Level: {plot_level}"
    )

    def get_query(level, league_number=27):
        query = (
            db.session.query(
                Game.time,
                Division.level,
                Division.league_number,
                Game.visitor_team_id,
                Game.home_team_id,
                Division.season_number,
            )
            .join(Division, Game.division_id == Division.id)
            .filter(Game.game_type != "Practice")
            .filter(Division.league_number == league_number)
        )

        if level != "all":
            query = query.filter(Division.level == level)

        return query

    def get_season_map():
        seasons = db.session.query(Season.season_number, Season.season_name).all()
        return {season.season_number: season.season_name for season in seasons}

    season_map = get_season_map()

    def get_team_map():
        teams = db.session.query(Team.id, Team.name).all()
        return {team.id: team.name for team in teams}

    team_map = get_team_map()

    if plot_type == "compare_levels_by_season":
        query_1 = get_query(level_1)
        query_2 = get_query(level_2)

        df_1 = pd.read_sql(query_1.statement, db.engine)
        df_2 = pd.read_sql(query_2.statement, db.engine)

        if df_1.empty and df_2.empty:
            return jsonify(
                {
                    "x": [],
                    "y_avg_1": [],
                    "y_avg_2": [],
                    "y_last_slot_1": [],
                    "y_last_slot_2": [],
                }
            )

        if df_1.empty:
            df_1 = pd.DataFrame(
                columns=["season_number", "time_minutes", "last_slot_game"]
            )
        if df_2.empty:
            df_2 = pd.DataFrame(
                columns=["season_number", "time_minutes", "last_slot_game"]
            )

        df_1["time_minutes"] = df_1["time"].apply(lambda x: x.hour * 60 + x.minute)
        df_2["time_minutes"] = df_2["time"].apply(lambda x: x.hour * 60 + x.minute)

        df_1["last_slot_game"] = df_1["time_minutes"] > 22 * 60 + 20
        df_2["last_slot_game"] = df_2["time_minutes"] > 22 * 60 + 20

        avg_start_time_1 = (
            df_1.groupby(["season_number"])["time_minutes"].mean().round()
        )
        avg_start_time_2 = (
            df_2.groupby(["season_number"])["time_minutes"].mean().round()
        )

        last_slot_percentage_1 = (
            df_1.groupby(["season_number"])["last_slot_game"].mean() * 100
        )
        last_slot_percentage_2 = (
            df_2.groupby(["season_number"])["last_slot_game"].mean() * 100
        )

        # Ensure unique X-axis values
        common_index = avg_start_time_1.index.intersection(avg_start_time_2.index)
        x_values = [
            f"{season_number} - {season_map[season_number]}"
            for season_number in common_index
        ]

        # Filter the data to only include common X values
        avg_start_time_1 = avg_start_time_1.loc[common_index]
        avg_start_time_2 = avg_start_time_2.loc[common_index]
        last_slot_percentage_1 = last_slot_percentage_1.loc[common_index]
        last_slot_percentage_2 = last_slot_percentage_2.loc[common_index]

        result = {
            "x": x_values,
            "y_avg_1": avg_start_time_1.tolist(),
            "y_avg_2": avg_start_time_2.tolist(),
            "y_last_slot_1": last_slot_percentage_1.round(1).tolist(),
            "y_last_slot_2": last_slot_percentage_2.round(1).tolist(),
        }

        # print("Debug Output (Compare Levels By Season):", result)  # Debug output

        return jsonify(result)
    else:
        query = get_query(plot_level, 1)

        df = pd.read_sql(query.statement, db.engine)

        # Add debug output to see distinct league_number values
        distinct_league_numbers = df["league_number"].unique()
        print(
            "Distinct league_number values in the DataFrame:", distinct_league_numbers
        )

        if df.empty:
            return jsonify({"x": [], "y_avg": [], "y_last_slot": []})

        df["time_minutes"] = df["time"].apply(lambda x: x.hour * 60 + x.minute)

        df["last_slot_game"] = df["time_minutes"] > 22 * 60 + 20

        # Duplicate rows for visitor and home teams
        df_visitor = df[
            [
                "time_minutes",
                "last_slot_game",
                "visitor_team_id",
                "season_number",
                "level",
            ]
        ].rename(columns={"visitor_team_id": "team_id"})
        df_home = df[
            ["time_minutes", "last_slot_game", "home_team_id", "season_number", "level"]
        ].rename(columns={"home_team_id": "team_id"})
        df = pd.concat([df_visitor, df_home])

        min_games_per_group = 2  # Minimum number of games to be included in the average
        avg_start_time = df.groupby(["season_number", "team_id"])["time_minutes"].agg(
            ["mean", "count"]
        )
        avg_start_time = avg_start_time[avg_start_time["count"] > min_games_per_group][
            "mean"
        ].round()
        last_slot_percentage = df.groupby(["season_number", "team_id"])[
            "last_slot_game"
        ].agg(["mean", "count"])
        last_slot_percentage = (
            last_slot_percentage[last_slot_percentage["count"] > min_games_per_group][
                "mean"
            ]
            * 100
        )

        # Ensure unique X-axis values
        x_values = [
            f"{season_number} - {season_map[season_number]}"
            for season_number in avg_start_time.index.get_level_values(
                "season_number"
            ).unique()
        ]

        teams = df[
            "team_id"
        ].unique()  # Get unique teams from the dataframe with the specified level
        teams = [
            team for team in teams if team_map.get(team)
        ]  # Filter out teams that map to empty name
        traces_avg = []
        traces_last_slot = []

        for team in teams:
            if team in avg_start_time.index.get_level_values("team_id"):
                team_avg_start_time = avg_start_time.xs(team, level="team_id").reindex(
                    avg_start_time.index.get_level_values("season_number").unique(),
                    fill_value=None,
                )
                team_last_slot_percentage = last_slot_percentage.xs(
                    team, level="team_id"
                ).reindex(
                    last_slot_percentage.index.get_level_values(
                        "season_number"
                    ).unique(),
                    fill_value=None,
                )
                team_name = team_map[team]

                # print(f"Debug: Processing Team {team_name}, team ID {team}")

                traces_avg.append(
                    {
                        "x": x_values,
                        "y": [None if pd.isna(y) else y for y in team_avg_start_time],
                        "mode": "lines+markers",
                        "name": team_name,
                    }
                )

                traces_last_slot.append(
                    {
                        "x": x_values,
                        "y": [
                            None if pd.isna(y) else y for y in team_last_slot_percentage
                        ],
                        "mode": "lines+markers",
                        "name": team_name,
                    }
                )

        result = {
            "x": x_values,
            "traces_avg": traces_avg,
            "traces_last_slot": traces_last_slot,
        }

        # print("Debug Output (Compare Teams By Level):", result)  # Debug output

        return jsonify(result)
