"""
Support blueprint — user help/feedback that creates GitHub issues.

Routes:
  POST /support/issue  — submit a bug report, feature request, or question
"""

import logging
import os

import requests
from flask import Blueprint, jsonify, request, session

logger = logging.getLogger(__name__)

support_bp = Blueprint("support", __name__)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = "kletskov/hockey-blast-frontend"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/issues"

LABEL_MAP = {
    "Bug": "bug",
    "Feature Request": "enhancement",
    "Question": "question",
}


@support_bp.route("/support/issue", methods=["POST"])
def create_issue():
    """Create a GitHub issue from user feedback."""
    data = request.get_json(silent=True) or {}

    title = (data.get("title") or "").strip()
    issue_type = (data.get("type") or "Bug").strip()
    description = (data.get("description") or "").strip()
    page = (data.get("page") or "").strip()

    if not title or not description:
        return jsonify({"ok": False, "error": "title and description are required"}), 400

    # Determine reporter — check Auth0 JWT first, then session, else anonymous
    reported_by = "anonymous"
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            import base64
            import json as _json
            token = auth_header[7:]
            payload_b64 = token.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = _json.loads(base64.b64decode(payload_b64))
            reported_by = (
                payload.get("email")
                or payload.get("name")
                or payload.get("sub")
                or "anonymous"
            )
        except Exception:
            pass
    elif session.get("user_name"):
        reported_by = session["user_name"]
    elif session.get("user_email"):
        reported_by = session["user_email"]

    issue_title = f"[{issue_type}] {title}"
    issue_body = (
        f"**Reported by:** {reported_by}\n"
        f"**Page:** {page}\n\n"
        f"{description}"
    )

    label = LABEL_MAP.get(issue_type, "question")

    try:
        response = requests.post(
            GITHUB_API_URL,
            json={
                "title": issue_title,
                "body": issue_body,
                "labels": [label],
            },
            headers={
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=10,
        )
        response.raise_for_status()
        issue_data = response.json()
        return jsonify({"ok": True, "issue_url": issue_data.get("html_url", "")})
    except requests.HTTPError as exc:
        logger.error("GitHub API error: %s — %s", exc, exc.response.text if exc.response else "")
        return jsonify({"ok": False, "error": "Failed to create GitHub issue"}), 502
    except Exception as exc:
        logger.error("Unexpected error creating GitHub issue: %s", exc)
        return jsonify({"ok": False, "error": "Unexpected error"}), 500
