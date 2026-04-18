"""
Auth proxy — forwards user-sync calls from hockey-blast.com to the sportsbook API.

The stats frontend does Auth0 auth client-side and has no direct write access
to the predictions database (where pred_users lives). After a successful login
the browser POSTs the ID token here; this blueprint forwards the call to the
sportsbook's /auth/sync endpoint, which upserts the user into the shared
pred_users table.

Using a same-origin proxy (rather than calling sportsbook.hockey-blast.com
cross-origin) avoids the Cloudflare Bot Fight Mode OPTIONS-preflight issue
that already forces the chat endpoints through chat_proxy.
"""

import requests
from flask import Blueprint, request, Response, jsonify

auth_proxy_bp = Blueprint("auth_proxy", __name__)

SPORTSBOOK_BASE = "http://127.0.0.1:5002"
TIMEOUT = 10


@auth_proxy_bp.route("/api/auth/sync", methods=["POST"])
def proxy_sync():
    """Forward POST /api/auth/sync → sportsbook /auth/sync with the Bearer token."""
    headers = {"Content-Type": "application/json"}
    auth = request.headers.get("Authorization")
    if auth:
        headers["Authorization"] = auth

    try:
        resp = requests.post(
            f"{SPORTSBOOK_BASE}/auth/sync",
            headers=headers,
            json=request.get_json(silent=True) or {},
            timeout=TIMEOUT,
        )
        return Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get("Content-Type", "application/json"),
        )
    except requests.exceptions.Timeout:
        return jsonify({"error": "Sportsbook API timed out"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 502
