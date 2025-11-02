"""
AI-powered search blueprint using Ollama LLM and MCP tools.

This endpoint is accessible but not linked from other pages (testing only).
"""

import asyncio
import json
import logging
from flask import Blueprint, render_template, request, jsonify
from hockey_blast_mcp.tools import human_basic, human_games, human_stats, human_events

logger = logging.getLogger(__name__)

ai_search_bp = Blueprint("ai_search", __name__)


# Tool registry mapping tool names to functions
TOOL_REGISTRY = {
    # Basic human info
    "get_human_by_id": human_basic.get_human_by_id,
    "search_humans_by_name": human_basic.search_humans_by_name,
    "get_human_skill_value": human_basic.get_human_skill_value,
    # Game participation
    "get_all_games_for_human": human_games.get_all_games_for_human,
    "get_skater_games": human_games.get_skater_games,
    "get_goalie_games": human_games.get_goalie_games,
    # Statistics
    "get_org_human_stats": human_stats.get_org_human_stats,
    "get_org_skater_stats": human_stats.get_org_skater_stats,
    "get_org_goalie_stats": human_stats.get_org_goalie_stats,
    # Events
    "get_goals_scored": human_events.get_goals_scored,
    "get_assists": human_events.get_assists,
    "get_points": human_events.get_points,
    "get_penalties": human_events.get_penalties,
}


def call_ollama(prompt: str, model: str = "llama3.1:8b") -> str:
    """
    Call Ollama API to get LLM response.

    Args:
        prompt: User query
        model: Ollama model name

    Returns:
        LLM response as string
    """
    import requests

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        logger.error(f"Ollama API error: {e}")
        raise


def build_tool_selection_prompt(user_query: str) -> str:
    """
    Build prompt for LLM to select appropriate tools.

    Args:
        user_query: Original user question

    Returns:
        Formatted prompt for tool selection
    """
    tools_description = """
Available tools for hockey statistics queries:

BASIC INFO:
- search_humans_by_name(search_term, limit=20) - Find players by name
- get_human_by_id(human_id) - Get player details by ID
- get_human_skill_value(human_id) - Get player skill rating

GAME PARTICIPATION:
- get_all_games_for_human(human_id, limit=100) - All games played
- get_skater_games(human_id, limit=100) - Games as skater
- get_goalie_games(human_id, limit=100) - Games as goalie

STATISTICS:
- get_org_human_stats(human_id) - Overall participation stats
- get_org_skater_stats(human_id) - Skater performance stats
- get_org_goalie_stats(human_id) - Goalie performance stats

EVENTS:
- get_goals_scored(human_id, limit=100) - Goals scored
- get_assists(human_id, limit=100) - Assists made
- get_points(human_id, limit=100) - Goals + assists
- get_penalties(human_id, limit=100) - Penalties taken

Your task: Given the user's query, determine which tools to call and in what order.
Respond with ONLY a JSON array of tool calls. Each tool call should be an object with:
- "tool": tool name
- "args": object with parameter names and values

Example response format:
[
  {{"tool": "search_humans_by_name", "args": {{"search_term": "Smith", "limit": 5}}}},
  {{"tool": "get_org_skater_stats", "args": {{"human_id": 12345}}}}
]

User query: {query}

Respond with ONLY the JSON array, no other text:"""

    return tools_description.format(query=user_query)


def build_answer_prompt(user_query: str, tool_results: list) -> str:
    """
    Build prompt for LLM to generate final answer from tool results.

    Args:
        user_query: Original user question
        tool_results: List of tool execution results

    Returns:
        Formatted prompt for answer generation
    """
    results_json = json.dumps(tool_results, indent=2)

    prompt = f"""You are a helpful hockey statistics assistant.

The user asked: "{user_query}"

I executed these tools and got the following data:

{results_json}

Please provide a clear, concise answer to the user's question based on this data.
Format numbers appropriately (e.g., "0.50 goals per game" not "0.5").
If the data shows the user wasn't found or has no stats, say so politely.

Answer:"""

    return prompt


async def execute_tool(tool_name: str, args: dict) -> dict:
    """
    Execute a single MCP tool.

    Args:
        tool_name: Name of tool to execute
        args: Tool arguments

    Returns:
        Tool result dictionary
    """
    if tool_name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        tool_func = TOOL_REGISTRY[tool_name]
        result = await tool_func(**args)
        return {"tool": tool_name, "args": args, "result": result}
    except Exception as e:
        logger.error(f"Tool execution error: {tool_name} - {e}")
        return {"tool": tool_name, "args": args, "error": str(e)}


async def execute_tools(tool_calls: list) -> list:
    """
    Execute multiple tools in sequence.

    Args:
        tool_calls: List of tool call specifications

    Returns:
        List of tool results
    """
    results = []
    for call in tool_calls:
        result = await execute_tool(call["tool"], call["args"])
        results.append(result)
    return results


def parse_tool_calls(llm_response: str) -> list:
    """
    Parse LLM response to extract tool calls.

    Args:
        llm_response: Raw LLM response

    Returns:
        List of tool call dictionaries
    """
    # Try to find JSON array in response
    try:
        # Look for JSON array markers
        start = llm_response.find("[")
        end = llm_response.rfind("]") + 1

        if start == -1 or end == 0:
            logger.error(f"No JSON array found in response: {llm_response}")
            return []

        json_str = llm_response[start:end]
        tool_calls = json.loads(json_str)

        if not isinstance(tool_calls, list):
            logger.error(f"Response is not a list: {tool_calls}")
            return []

        return tool_calls
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse tool calls: {e}\nResponse: {llm_response}")
        return []


@ai_search_bp.route("/ai-search", methods=["GET", "POST"])
def ai_search():
    """
    AI search endpoint with text box interface.

    GET: Shows search form
    POST: Processes search query with LLM + MCP tools
    """
    if request.method == "GET":
        return render_template("ai_search.html")

    # POST: Process search query
    user_query = request.form.get("query", "").strip()

    if not user_query:
        return jsonify({"error": "Please provide a search query"}), 400

    try:
        # Step 1: Ask LLM to select tools
        logger.info(f"AI Search Query: {user_query}")
        tool_selection_prompt = build_tool_selection_prompt(user_query)
        tool_selection_response = call_ollama(tool_selection_prompt)
        logger.info(f"Tool selection response: {tool_selection_response}")

        # Step 2: Parse tool calls
        tool_calls = parse_tool_calls(tool_selection_response)
        if not tool_calls:
            return jsonify({
                "error": "Could not determine which tools to use for your query",
                "debug": {
                    "query": user_query,
                    "llm_response": tool_selection_response,
                }
            }), 500

        logger.info(f"Parsed tool calls: {tool_calls}")

        # Step 3: Execute tools
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tool_results = loop.run_until_complete(execute_tools(tool_calls))
        loop.close()

        logger.info(f"Tool results: {tool_results}")

        # Step 4: Ask LLM to generate answer from results
        answer_prompt = build_answer_prompt(user_query, tool_results)
        final_answer = call_ollama(answer_prompt)

        logger.info(f"Final answer: {final_answer}")

        # Return JSON response
        return jsonify({
            "query": user_query,
            "answer": final_answer,
            "debug": {
                "tool_calls": tool_calls,
                "tool_results": tool_results,
            }
        })

    except Exception as e:
        logger.error(f"AI search error: {e}", exc_info=True)
        return jsonify({
            "error": f"Search failed: {str(e)}",
            "query": user_query,
        }), 500
