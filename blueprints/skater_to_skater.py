
from flask import Blueprint, render_template, request
from hockey_blast_common_lib.h2h_models import SkaterToSkaterStats
from hockey_blast_common_lib.models import Human, Level, db
from hockey_blast_common_lib.stats_models import LevelStatsSkater

skater_to_skater_bp = Blueprint("skater_to_skater", __name__)


def format_date(date):
    if date:
        return date.strftime("%m/%d/%Y")
    return "Unknown"


@skater_to_skater_bp.route("/", methods=["GET"])
def skater_to_skater():
    human_id_1 = request.args.get("human_id_1", type=int)
    human_id_2 = request.args.get("human_id_2", type=int)

    if not human_id_1 or not human_id_2:
        return render_template(
            "skater_to_skater.html",
            error="Please provide both human_id_1 and human_id_2 parameters",
        )

    # Get human names
    human1 = db.session.query(Human).filter(Human.id == human_id_1).first()
    human2 = db.session.query(Human).filter(Human.id == human_id_2).first()

    if not human1 or not human2:
        return render_template(
            "skater_to_skater.html", error="One or both skaters not found"
        )

    # Get head-to-head stats
    # SkaterToSkaterStats always stores with skater1_id < skater2_id
    if human_id_1 < human_id_2:
        s2s_stats = (
            db.session.query(SkaterToSkaterStats)
            .filter(
                SkaterToSkaterStats.skater1_id == human_id_1,
                SkaterToSkaterStats.skater2_id == human_id_2,
            )
            .first()
        )
        is_reversed = False
    else:
        s2s_stats = (
            db.session.query(SkaterToSkaterStats)
            .filter(
                SkaterToSkaterStats.skater1_id == human_id_2,
                SkaterToSkaterStats.skater2_id == human_id_1,
            )
            .first()
        )
        is_reversed = True

    if not s2s_stats:
        # No head-to-head stats exist, but we can still show level comparisons
        # Create empty stats structure
        human1_name = (
            f"{human1.first_name} {human1.middle_name} {human1.last_name}".strip()
        )
        human2_name = (
            f"{human2.first_name} {human2.middle_name} {human2.last_name}".strip()
        )

        stats = {
            "games_against": 0,
            "games_tied_against": 0,
            "skater1_wins": 0,
            "skater2_wins": 0,
            "skater1_goals": 0,
            "skater2_goals": 0,
            "skater1_assists": 0,
            "skater2_assists": 0,
            "skater1_points": 0,
            "skater2_points": 0,
            "skater1_penalties": 0,
            "skater2_penalties": 0,
            "skater1_goals_per_game": 0.0,
            "skater2_goals_per_game": 0.0,
            "skater1_assists_per_game": 0.0,
            "skater2_assists_per_game": 0.0,
            "skater1_points_per_game": 0.0,
            "skater2_points_per_game": 0.0,
            "skater1_penalties_per_game": 0.0,
            "skater2_penalties_per_game": 0.0,
            "skater1_win_percentage": 0.0,
            "skater2_win_percentage": 0.0,
        }

        # Get level comparisons
        level_comparisons = get_level_comparisons(human_id_1, human_id_2)

        return render_template(
            "skater_to_skater.html",
            human1=human1,
            human2=human2,
            human1_name=human1_name,
            human2_name=human2_name,
            stats=stats,
            level_comparisons=level_comparisons,
        )

    human1_name = f"{human1.first_name} {human1.middle_name} {human1.last_name}".strip()
    human2_name = f"{human2.first_name} {human2.middle_name} {human2.last_name}".strip()

    # Calculate additional statistics
    stats = {}

    # Basic game stats
    stats["games_against"] = s2s_stats.games_against
    stats["games_tied_against"] = s2s_stats.games_tied_against

    # Wins/losses - need to handle reversed IDs
    if is_reversed:
        stats["skater1_wins"] = s2s_stats.skater2_wins_vs_skater1
        stats["skater2_wins"] = s2s_stats.skater1_wins_vs_skater2
        stats["skater1_goals"] = s2s_stats.skater2_goals_against_skater1
        stats["skater2_goals"] = s2s_stats.skater1_goals_against_skater2
        stats["skater1_assists"] = s2s_stats.skater2_assists_against_skater1
        stats["skater2_assists"] = s2s_stats.skater1_assists_against_skater2
        stats["skater1_penalties"] = s2s_stats.skater2_penalties_against_skater1
        stats["skater2_penalties"] = s2s_stats.skater1_penalties_against_skater2
    else:
        stats["skater1_wins"] = s2s_stats.skater1_wins_vs_skater2
        stats["skater2_wins"] = s2s_stats.skater2_wins_vs_skater1
        stats["skater1_goals"] = s2s_stats.skater1_goals_against_skater2
        stats["skater2_goals"] = s2s_stats.skater2_goals_against_skater1
        stats["skater1_assists"] = s2s_stats.skater1_assists_against_skater2
        stats["skater2_assists"] = s2s_stats.skater2_assists_against_skater1
        stats["skater1_penalties"] = s2s_stats.skater1_penalties_against_skater2
        stats["skater2_penalties"] = s2s_stats.skater2_penalties_against_skater1

    # Calculate points
    stats["skater1_points"] = stats["skater1_goals"] + stats["skater1_assists"]
    stats["skater2_points"] = stats["skater2_goals"] + stats["skater2_assists"]

    # Calculate per-game averages
    if stats["games_against"] > 0:
        stats["skater1_goals_per_game"] = (
            stats["skater1_goals"] / stats["games_against"]
        )
        stats["skater2_goals_per_game"] = (
            stats["skater2_goals"] / stats["games_against"]
        )
        stats["skater1_assists_per_game"] = (
            stats["skater1_assists"] / stats["games_against"]
        )
        stats["skater2_assists_per_game"] = (
            stats["skater2_assists"] / stats["games_against"]
        )
        stats["skater1_points_per_game"] = (
            stats["skater1_points"] / stats["games_against"]
        )
        stats["skater2_points_per_game"] = (
            stats["skater2_points"] / stats["games_against"]
        )
        stats["skater1_penalties_per_game"] = (
            stats["skater1_penalties"] / stats["games_against"]
        )
        stats["skater2_penalties_per_game"] = (
            stats["skater2_penalties"] / stats["games_against"]
        )
    else:
        stats["skater1_goals_per_game"] = 0
        stats["skater2_goals_per_game"] = 0
        stats["skater1_assists_per_game"] = 0
        stats["skater2_assists_per_game"] = 0
        stats["skater1_points_per_game"] = 0
        stats["skater2_points_per_game"] = 0
        stats["skater1_penalties_per_game"] = 0
        stats["skater2_penalties_per_game"] = 0

    # Calculate winning percentages
    non_tied_games = stats["games_against"] - stats["games_tied_against"]
    if non_tied_games > 0:
        stats["skater1_win_percentage"] = (stats["skater1_wins"] / non_tied_games) * 100
        stats["skater2_win_percentage"] = (stats["skater2_wins"] / non_tied_games) * 100
    else:
        stats["skater1_win_percentage"] = 0
        stats["skater2_win_percentage"] = 0

    # Get level comparisons
    level_comparisons = get_level_comparisons(human_id_1, human_id_2)

    return render_template(
        "skater_to_skater.html",
        human1=human1,
        human2=human2,
        human1_name=human1_name,
        human2_name=human2_name,
        stats=stats,
        level_comparisons=level_comparisons,
    )


def get_level_comparisons(human_id_1, human_id_2):
    """Get level statistics for both skaters in overlapping levels"""
    # Get level stats for both skaters
    skater1_levels = (
        db.session.query(LevelStatsSkater)
        .filter(LevelStatsSkater.human_id == human_id_1)
        .all()
    )

    skater2_levels = (
        db.session.query(LevelStatsSkater)
        .filter(LevelStatsSkater.human_id == human_id_2)
        .all()
    )

    # Find overlapping levels
    skater1_level_ids = {stats.level_id for stats in skater1_levels}
    skater2_level_ids = {stats.level_id for stats in skater2_levels}
    overlapping_level_ids = skater1_level_ids.intersection(skater2_level_ids)

    if not overlapping_level_ids:
        return []

    # Get level names
    levels = db.session.query(Level).filter(Level.id.in_(overlapping_level_ids)).all()
    level_names = {level.id: level.level_name for level in levels}

    # Create comparison data
    comparisons = []

    for level_id in overlapping_level_ids:
        skater1_stats = next(
            (s for s in skater1_levels if s.level_id == level_id), None
        )
        skater2_stats = next(
            (s for s in skater2_levels if s.level_id == level_id), None
        )

        if skater1_stats and skater2_stats:
            comparison = {
                "level_name": level_names.get(level_id, "Unknown Level"),
                "skater1_games_played": skater1_stats.games_participated,
                "skater2_games_played": skater2_stats.games_participated,
                "skater1_goals_per_game": skater1_stats.goals_per_game,
                "skater2_goals_per_game": skater2_stats.goals_per_game,
                "skater1_assists_per_game": skater1_stats.assists_per_game,
                "skater2_assists_per_game": skater2_stats.assists_per_game,
                "skater1_points_per_game": skater1_stats.points_per_game,
                "skater2_points_per_game": skater2_stats.points_per_game,
                "skater1_penalties_per_game": skater1_stats.penalties_per_game,
                "skater2_penalties_per_game": skater2_stats.penalties_per_game,
                "skater1_gm_penalties_per_game": skater1_stats.gm_penalties_per_game,
                "skater2_gm_penalties_per_game": skater2_stats.gm_penalties_per_game,
            }
            comparisons.append(comparison)

    # Sort by level name
    comparisons.sort(key=lambda x: x["level_name"])

    return comparisons
