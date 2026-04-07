"""
Chat proxy — forwards requests from hockey-blast.com to sportsbook.hockey-blast.com.

Avoids CORS preflight issues caused by Cloudflare Bot Fight Mode blocking OPTIONS
requests when the stats site calls the sportsbook API cross-origin.
"""
import requests
from flask import Blueprint, request, Response, jsonify

chat_proxy_bp = Blueprint("chat_proxy", __name__)

SPORTSBOOK_BASE = "https://sportsbook.hockey-blast.com"
TIMEOUT = 90  # Chat can take a while (Bedrock round trips)


def _proxy(path):
    """Forward the request to the sportsbook API and stream the response back."""
    url = f"{SPORTSBOOK_BASE}{path}"

    # Forward auth header if present
    headers = {"Content-Type": "application/json"}
    auth = request.headers.get("Authorization")
    if auth:
        headers["Authorization"] = auth

    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            json=request.get_json(silent=True) if request.method == "POST" else None,
            params=request.args,
            timeout=TIMEOUT,
        )
        return Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get("Content-Type", "application/json"),
        )
    except requests.exceptions.Timeout:
        return jsonify({"error": "Chat engine timed out"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@chat_proxy_bp.route("/api/chat/message", methods=["POST"])
def proxy_message():
    return _proxy("/api/chat/message")


@chat_proxy_bp.route("/api/chat/history", methods=["GET"])
def proxy_history():
    return _proxy("/api/chat/history")


@chat_proxy_bp.route("/api/chat/feedback/<int:message_id>", methods=["POST"])
def proxy_feedback(message_id):
    return _proxy(f"/api/chat/feedback/{message_id}")
