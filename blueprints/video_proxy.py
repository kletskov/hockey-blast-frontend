"""Video-highlights proxy — streams video from the internal livebarn-serve service.

Hides the internal video service URI from end users.  The /status endpoint
is lightweight (JSON); the /video endpoint streams the MP4 with full
Range-request support so browsers can seek inside the player.
"""
import os
import re

import requests as http_requests
from flask import Blueprint, Response, jsonify, render_template, request
from hockey_blast_common_lib.models import Game, Team, db

video_proxy_bp = Blueprint("video_proxy", __name__)

VIDEO_SERVICE_BASE = os.environ.get("VIDEO_SERVICE_URL", "http://127.0.0.1:5004")
STATUS_TIMEOUT = 5
VIDEO_TIMEOUT = 300


def _download_filename(game_id: int) -> str:
    """Build a descriptive filename like 'highlights_362030_Sharks_vs_Wolves_2026-04-08_2000.mp4'."""
    try:
        game = db.session.query(Game).filter(Game.id == game_id).first()
        if game:
            home = db.session.query(Team).filter(Team.id == game.home_team_id).first()
            away = db.session.query(Team).filter(Team.id == game.visitor_team_id).first()
            home_name = re.sub(r'[^\w]+', '_', (home.name if home else 'Home')).strip('_')
            away_name = re.sub(r'[^\w]+', '_', (away.name if away else 'Away')).strip('_')
            date_str = game.date.strftime('%Y-%m-%d') if game.date else ''
            time_str = game.time.strftime('%H%M') if game.time else ''
            return f"highlights_{game_id}_{home_name}_vs_{away_name}_{date_str}_{time_str}.mp4"
    except Exception:
        pass
    return f"highlights_{game_id}.mp4"


@video_proxy_bp.route("/highlights/<int:game_id>")
def highlights_viewer(game_id):
    filename = _download_filename(game_id)
    return render_template("highlights_viewer.html", game_id=game_id, download_filename=filename)


@video_proxy_bp.route("/api/highlights/<int:game_id>/status")
def proxy_status(game_id):
    url = f"{VIDEO_SERVICE_BASE}/api/highlights/{game_id}/status"
    try:
        resp = http_requests.get(url, timeout=STATUS_TIMEOUT)
        return Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get("Content-Type", "application/json"),
        )
    except Exception:
        return jsonify({"available": False}), 502


@video_proxy_bp.route("/api/highlights/<int:game_id>/video")
def proxy_video(game_id):
    headers = {}
    range_header = request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header

    url = f"{VIDEO_SERVICE_BASE}/api/highlights/{game_id}/video"
    try:
        upstream = http_requests.get(
            url, headers=headers, stream=True, timeout=VIDEO_TIMEOUT
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    response_headers = {}
    for h in (
        "Content-Type",
        "Content-Length",
        "Content-Range",
        "Content-Disposition",
        "Accept-Ranges",
        "Cache-Control",
    ):
        if h in upstream.headers:
            response_headers[h] = upstream.headers[h]

    # ?dl=1 forces download (needed for iOS Safari)
    if request.args.get("dl"):
        fname = _download_filename(game_id)
        response_headers["Content-Disposition"] = (
            f'attachment; filename="{fname}"'
        )

    return Response(
        upstream.iter_content(chunk_size=64 * 1024),
        status=upstream.status_code,
        headers=response_headers,
    )
