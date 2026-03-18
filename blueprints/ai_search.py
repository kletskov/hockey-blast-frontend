"""
AI-powered hockey search — powered by Bedrock native tool use.
"""

import logging
import os

from flask import Blueprint, render_template, request, jsonify

logger = logging.getLogger(__name__)

ai_search_bp = Blueprint("ai_search", __name__)


@ai_search_bp.route("/api/chat", methods=["POST"])
def chat_api():
    """Floating chat widget endpoint — POST {query, history[]}"""
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    history = data.get("history") or []

    if not query:
        return jsonify({"error": "query is required"}), 400

    try:
        from hockey_blast_mcp.bedrock_chat import chat
        result = chat(query, history=history)
        return jsonify({
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
