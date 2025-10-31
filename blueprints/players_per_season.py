import matplotlib
from flask import Blueprint, render_template
from flask_table import Col, Table

matplotlib.use("Agg")
import base64
import io

import matplotlib.pyplot as plt
from hockey_blast_common_lib.models import (Division, Game,
                                            GameRoster, Season, db)

players_per_season_bp = Blueprint("players_per_season", __name__)


class SeasonTable(Table):
    season_number = Col("Season Number")
    season_name = Col("Season Name")
    start_date = Col("Start Date")
    end_date = Col("End Date")
    num_players = Col("Number of Players")


class SeasonItem(object):
    def __init__(self, season_number, season_name, start_date, end_date, num_players):
        self.season_number = season_number
        self.season_name = season_name
        self.start_date = start_date
        self.end_date = end_date
        self.num_players = num_players


@players_per_season_bp.route("/players_per_season")
def players_per_season():
    results = (
        db.session.query(
            Season.season_number,
            Season.season_name,
            Season.start_date,
            Season.end_date,
            db.func.count(GameRoster.human_id.distinct()).label("num_players"),
        )
        .join(Division, Division.season_number == Season.season_number)
        .join(Game, Game.division_id == Division.id)
        .join(GameRoster, GameRoster.game_id == Game.id)
        .filter(~Season.season_number.in_([4, 44, 48]))
        .group_by(
            Season.season_number, Season.season_name, Season.start_date, Season.end_date
        )
        .all()
    )

    items = [
        SeasonItem(
            result.season_number,
            result.season_name,
            result.start_date,
            result.end_date,
            result.num_players,
        )
        for result in results
    ]
    table = SeasonTable(items)

    # Generate plot
    season_names = [item.season_name for item in items]
    num_players = [item.num_players for item in items]
    plt.figure(figsize=(20, 10))  # Increase figure size
    plt.plot(season_names, num_players, marker="o")
    plt.xlabel("Season Name")
    plt.ylabel("Number of Players")
    plt.title("Number of Players per Season")
    plt.grid(True)
    plt.xticks(
        rotation=45, ha="right", fontsize=10
    )  # Rotate X-axis labels for better readability and adjust font size

    # Annotate each point with the Y-axis value
    for i, txt in enumerate(num_players):
        plt.annotate(
            txt,
            (season_names[i], num_players[i]),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
        )

    # Save plot to a string buffer
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plot_url = base64.b64encode(buf.getvalue()).decode("utf8")
    plt.close()

    return render_template(
        "players_per_season.html", players_per_season=items, plot_url=plot_url
    )
