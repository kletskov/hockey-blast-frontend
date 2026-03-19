"""
AI-powered hockey search — powered by Bedrock native tool use.
"""

import logging
import os

from flask import Blueprint, render_template, request, jsonify

logger = logging.getLogger(__name__)

ai_search_bp = Blueprint("ai_search", __name__)


def _get_user_from_token(req):
    """Extract user identifier from Auth0 JWT if present. Returns None if no/invalid token."""
    auth_header = req.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header[7:]
    try:
        import json, base64
        payload_b64 = token.split('.')[1]
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.b64decode(payload_b64))
        return payload.get('email') or payload.get('name') or payload.get('sub')
    except Exception:
        return None


@ai_search_bp.route("/api/chat/feedback", methods=["POST"])
def chat_feedback():
    """Store like/dislike feedback for a chat message."""
    data = request.get_json(silent=True) or {}
    message_id = data.get("message_id")
    rating = data.get("rating")  # 'like' or 'dislike'
    comment = data.get("comment", "")

    if not message_id or rating not in ("like", "dislike"):
        return jsonify({"error": "message_id and rating required"}), 400

    user_id = _get_user_from_token(request)

    try:
        import psycopg2, os
        conn = psycopg2.connect(
            host=os.environ.get("PRED_DB_HOST", "localhost"),
            user=os.environ.get("PRED_DB_USER", "foxyclaw"),
            password=os.environ.get("PRED_DB_PASSWORD", "foxyhockey2026"),
            dbname=os.environ.get("PRED_DB_NAME", "hockey_blast_predictions"),
        )
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS blast_chat_feedback (
                id SERIAL PRIMARY KEY,
                message_id TEXT NOT NULL UNIQUE,
                rating VARCHAR(10) NOT NULL,
                comment TEXT DEFAULT '',
                user_id TEXT DEFAULT NULL,
                source VARCHAR(20) DEFAULT 'frontend',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            INSERT INTO blast_chat_feedback (message_id, rating, comment, user_id, source)
            VALUES (%s, %s, %s, %s, 'frontend')
            ON CONFLICT (message_id) DO UPDATE SET rating = EXCLUDED.rating, comment = EXCLUDED.comment, user_id = EXCLUDED.user_id
        """, (str(message_id), rating, comment or "", user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Feedback storage failed: {e}")
        # Fail gracefully
    return jsonify({"ok": True})


@ai_search_bp.route("/api/chat", methods=["POST"])
def chat_api():
    """Floating chat widget endpoint — POST {query, history[]}"""
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    history = data.get("history") or []

    if not query:
        return jsonify({"error": "query is required"}), 400

    user_id = _get_user_from_token(request)
    logger.info(f"Chat query from user={user_id or 'anonymous'}: {query[:80]}")

    try:
        from hockey_blast_mcp.bedrock_chat import chat
        result = chat(query, history=history)
        import uuid
        message_id = str(uuid.uuid4())
        return jsonify({
            "message_id": message_id,
            "answer": result["answer"],
            "tools_used": result.get("tools_used", []),
        })
    except Exception as e:
        logger.error(f"Chat API error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@ai_search_bp.route("/ai-search", methods=["GET", "POST"])
def ai_search():
    if request.method == "GET":
        return render_template("ai_search.html")

    user_query = request.form.get("query", "").strip()
    if not user_query:
        return jsonify({"error": "Please provide a search query"}), 400

    try:
        from hockey_blast_mcp.bedrock_chat import chat
        result = chat(user_query)
        return jsonify({
            "query": user_query,
            "answer": result["answer"],
            "debug": {
                "tools_used": result["tools_used"],
                "iterations": result["iterations"],
            }
        })
    except Exception as e:
        logger.error(f"AI search error: {e}", exc_info=True)
        return jsonify({"error": str(e), "query": user_query}), 500
