"""Video-highlights proxy — streams video from the internal livebarn-serve service.

Hides the internal video service URI from end users.  The /status endpoint
is lightweight (JSON); the /video endpoint streams the MP4 with full
Range-request support so browsers can seek inside the player.
"""
import os

import requests as http_requests
from flask import Blueprint, Response, jsonify, render_template, request

video_proxy_bp = Blueprint("video_proxy", __name__)

VIDEO_SERVICE_BASE = os.environ.get("VIDEO_SERVICE_URL", "http://127.0.0.1:5004")
STATUS_TIMEOUT = 5
VIDEO_TIMEOUT = 300


@video_proxy_bp.route("/highlights/<int:game_id>")
def highlights_viewer(game_id):
    return render_template("highlights_viewer.html", game_id=game_id)


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
        response_headers["Content-Disposition"] = (
            f'attachment; filename="highlights_{game_id}.mp4"'
        )

    return Response(
        upstream.iter_content(chunk_size=64 * 1024),
        status=upstream.status_code,
        headers=response_headers,
    )
