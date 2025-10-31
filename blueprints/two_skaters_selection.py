from flask import Blueprint, redirect, render_template, request, url_for
from hockey_blast_common_lib.models import Human, HumanAlias, db
from hockey_blast_common_lib.stats_models import OrgStatsSkater

from options import MAX_HUMAN_SEARCH_RESULTS

two_skaters_selection_bp = Blueprint("two_skaters_selection", __name__)


def search_skaters(first_name, last_name):
    """Search for humans who have skater records in OrgStatsSkater"""
    query = db.session.query(Human).join(
        OrgStatsSkater, Human.id == OrgStatsSkater.human_id
    )

    if first_name:
        query = query.filter(Human.first_name.ilike(f"%{first_name}%"))
    if last_name:
        query = query.filter(Human.last_name.ilike(f"%{last_name}%"))

    # Apply limit and get distinct results
    results = query.distinct().limit(MAX_HUMAN_SEARCH_RESULTS).all()

    search_results = []
    for player in results:
        aliases = (
            db.session.query(HumanAlias).filter(HumanAlias.human_id == player.id).all()
        )
        alias_names = [
            f"{alias.first_name} {alias.middle_name} {alias.last_name}".strip()
            for alias in aliases
            if f"{alias.first_name} {alias.middle_name} {alias.last_name}".strip()
            != f"{player.first_name} {player.middle_name} {player.last_name}".strip()
        ]
        alias_text = f" A.K.A. {', '.join(alias_names)}" if alias_names else ""
        player_name = (
            f"{player.first_name} {player.middle_name} {player.last_name}".strip()
        )

        search_results.append(
            {
                "id": player.id,
                "name": player_name,
                "display_name": f"{player_name}{alias_text}",
            }
        )

    return search_results


@two_skaters_selection_bp.route("/", methods=["GET", "POST"])
def select_skaters():
    selected_skater_1 = request.args.get("skater_1_id", type=int)
    selected_skater_1_name = request.args.get("skater_1_name")
    search_results = None
    stage = 1 if not selected_skater_1 else 2

    if request.method == "POST":
        if "search" in request.form:
            # Handle search
            first_name = request.form.get("first_name")
            last_name = request.form.get("last_name")

            if first_name or last_name:
                search_results = search_skaters(first_name, last_name)
                if not search_results:
                    search_results = []

        elif "select_skater_1" in request.form:
            # Handle first skater selection
            skater_id = request.form.get("skater_id", type=int)
            skater_name = request.form.get("skater_name")
            return redirect(
                url_for(
                    "two_skaters_selection.select_skaters",
                    skater_1_id=skater_id,
                    skater_1_name=skater_name,
                )
            )

        elif "select_skater_2" in request.form:
            # Handle second skater selection and redirect to comparison
            skater_2_id = request.form.get("skater_id", type=int)
            return redirect(
                url_for(
                    "skater_to_skater.skater_to_skater",
                    human_id_1=selected_skater_1,
                    human_id_2=skater_2_id,
                )
            )

    return render_template(
        "two_skaters_selection.html",
        stage=stage,
        selected_skater_1_id=selected_skater_1,
        selected_skater_1_name=selected_skater_1_name,
        search_results=search_results,
    )
