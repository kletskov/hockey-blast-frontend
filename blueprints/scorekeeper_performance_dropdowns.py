from flask import Blueprint, jsonify
from hockey_blast_common_lib.models import db, Organization, Level, Division, Season, Team, Human
from hockey_blast_common_lib.stats_models import OrgStatsScorekeeper
from hockey_blast_common_lib.stats_utils import ALL_ORGS_ID

def filter_levels(org_id, human_id=None):
    if org_id == ALL_ORGS_ID:
        # For ALL_ORGS_ID, get all levels (scorekeeper quality is org-wide)
        if human_id:
            # Check if this human has org-level scorekeeper stats anywhere
            org_stats = db.session.query(OrgStatsScorekeeper).filter(
                OrgStatsScorekeeper.human_id == human_id
            ).first()
            if org_stats:
                levels = db.session.query(Level).all()
            else:
                levels = []
        else:
            levels = db.session.query(Level).all()
    else:
        # For specific org, get levels from divisions in that org
        if human_id:
            # Check if this human has scorekeeper stats for this org
            org_stats = db.session.query(OrgStatsScorekeeper).filter(
                OrgStatsScorekeeper.org_id == org_id,
                OrgStatsScorekeeper.human_id == human_id
            ).first()
            if org_stats:
                levels = db.session.query(Level).join(Division, Level.id == Division.level_id).filter(
                    Division.org_id == org_id
                ).distinct().all()
            else:
                levels = []
        else:
            levels = db.session.query(Level).join(Division, Level.id == Division.level_id).filter(
                Division.org_id == org_id
            ).distinct().all()

    return jsonify([{"id": level.id, "level_name": level.level_name} for level in levels])

def filter_seasons(org_id, level_id, human_id=None):
    query = db.session.query(Season).join(Division, Season.id == Division.season_id)

    if human_id:
        # Check if this human has scorekeeper stats for this org
        if org_id != ALL_ORGS_ID:
            org_stats = db.session.query(OrgStatsScorekeeper).filter(
                OrgStatsScorekeeper.org_id == org_id,
                OrgStatsScorekeeper.human_id == human_id
            ).first()
            if not org_stats:
                return jsonify([])
        else:
            org_stats = db.session.query(OrgStatsScorekeeper).filter(
                OrgStatsScorekeeper.human_id == human_id
            ).first()
            if not org_stats:
                return jsonify([])

    if org_id != ALL_ORGS_ID:
        query = query.filter(Division.org_id == org_id)

    if level_id:
        query = query.filter(Division.level_id == level_id)

    seasons = query.distinct().all()
    return jsonify([{"id": season.id, "season_name": season.season_name} for season in seasons])

def filter_teams(org_id, level_id, season_id, human_id=None):
    # For scorekeepers, teams are less relevant, but we can still provide this functionality
    query = db.session.query(Team).join(Division).filter()

    if org_id != ALL_ORGS_ID:
        query = query.filter(Division.org_id == org_id)

    if level_id:
        query = query.filter(Division.level_id == level_id)

    if season_id:
        query = query.filter(Division.season_id == season_id)

    teams = query.distinct().all()
    return jsonify([{"id": team.id, "name": team.name} for team in teams])

def get_levels_for_scorekeeper_in_org(org_id, human_id):
    if not human_id:
        return []

    if org_id == ALL_ORGS_ID:
        # Check if this human has scorekeeper stats for any org
        org_stats = db.session.query(OrgStatsScorekeeper).filter(
            OrgStatsScorekeeper.human_id == human_id
        ).first()
        if org_stats:
            levels = db.session.query(Level).all()
        else:
            levels = []
    else:
        # Check if this human has scorekeeper stats for this specific org
        org_stats = db.session.query(OrgStatsScorekeeper).filter(
            OrgStatsScorekeeper.org_id == org_id,
            OrgStatsScorekeeper.human_id == human_id
        ).first()
        if org_stats:
            levels = db.session.query(Level).join(Division, Level.id == Division.level_id).filter(
                Division.org_id == org_id
            ).distinct().all()
        else:
            levels = []

    return [{"id": level.id, "level_name": level.level_name} for level in levels]

def get_divisions_and_seasons(org_id, level_id=None, human_id=None):
    query = db.session.query(Division, Season).join(Season, Division.season_id == Season.id)

    if human_id:
        # Check if this human has scorekeeper stats for this org
        if org_id != ALL_ORGS_ID:
            org_stats = db.session.query(OrgStatsScorekeeper).filter(
                OrgStatsScorekeeper.org_id == org_id,
                OrgStatsScorekeeper.human_id == human_id
            ).first()
            if not org_stats:
                return [], []
        else:
            org_stats = db.session.query(OrgStatsScorekeeper).filter(
                OrgStatsScorekeeper.human_id == human_id
            ).first()
            if not org_stats:
                return [], []

    if org_id != ALL_ORGS_ID:
        query = query.filter(Division.org_id == org_id)

    if level_id:
        query = query.filter(Division.level_id == level_id)

    results = query.all()
    divisions = [{"id": div.id, "level": div.level} for div, season in results]
    seasons = [{"id": season.id, "season_name": season.season_name} for div, season in results]

    return divisions, seasons