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

HOW SEARCH WORKS:
- search_humans_by_name searches BOTH first_name and last_name fields
- It uses substring matching (case-insensitive)
- Example: "Kletskov" will find "Pavel Kletskov", "Max Kletskov", etc.
- Example: "Pavel" will find "Pavel Kletskov", "Pavel Smith", etc.

CRITICAL RULES FOR NAME QUERIES:
1. If user asks about "FirstName LastName", search by LAST NAME ONLY
2. You will get multiple results (family members, same last name)
3. LOOK at the search results and find the one matching the FIRST NAME
4. Extract that person's human_id for subsequent calls
5. NEVER invent or hallucinate human_id values

WORKFLOW for "Show me Pavel Kletskov's stats":
Step 1: Search by last name
[
  {{"tool": "search_humans_by_name", "args": {{"search_term": "Kletskov", "limit": 10}}}}
]

Step 2: After seeing results like:
- {{"id": 117076, "first_name": "Pavel", "last_name": "Kletskov"}}
- {{"id": 119999, "first_name": "Max", "last_name": "Kletskov"}}

You pick the one where first_name matches "Pavel", which is id 117076

Step 3: Use that ID:
[
  {{"tool": "get_org_skater_stats", "args": {{"human_id": 117076}}}}
]

For "Find players named Smith":
[
  {{"tool": "search_humans_by_name", "args": {{"search_term": "Smith", "limit": 20}}}}
]
Then STOP - user just wants the list, not detailed stats

User query: {query}

Respond with ONLY the JSON array for the FIRST step:"""

    return tools_description.format(query=user_query)


def build_next_step_prompt(user_query: str, previous_results: list) -> str:
    """
    Build prompt for LLM to select next tools based on previous results.

    Args:
        user_query: Original user question
        previous_results: Results from previous tool executions

    Returns:
        Formatted prompt for next tool selection
    """
    results_summary = json.dumps(previous_results, indent=2)

    prompt = f"""You are continuing to answer this query: "{user_query}"

You've already executed these tools and got these results:

{results_summary}

Based on these results, what tools should you call NEXT?

CRITICAL RULES:
1. If you got search results with multiple people, LOOK at first_name to match the query
2. Use the CORRECT human_id from the person matching the first name in the query
3. Do NOT just pick the first result - find the RIGHT person
4. Do NOT invent IDs
5. If you have all the data needed, return an empty array: []

Example: Query was "Show me Pavel Kletskov's stats"
- Search returned: [{{"id": 117076, "first_name": "Pavel"}}, {{"id": 119999, "first_name": "Max"}}]
- You need Pavel, so use id 117076 (NOT 119999!)

Available tools:
- get_human_by_id(human_id)
- get_org_human_stats(human_id)
- get_org_skater_stats(human_id)
- get_org_goalie_stats(human_id)
- get_skater_games(human_id, limit)
- get_goalie_games(human_id, limit)
- get_goals_scored(human_id, limit)
- get_assists(human_id, limit)
- get_penalties(human_id, limit)

Respond with ONLY a JSON array of tool calls, or [] if done:"""

    return prompt


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
    POST: Processes search query with LLM + MCP tools using multi-step agentic loop
    """
    if request.method == "GET":
        return render_template("ai_search.html")

    # POST: Process search query
    user_query = request.form.get("query", "").strip()

    if not user_query:
        return jsonify({"error": "Please provide a search query"}), 400

    try:
        logger.info(f"AI Search Query: {user_query}")

        all_tool_calls = []
        all_tool_results = []

        # Multi-step agentic loop (max 3 iterations)
        for iteration in range(3):
            logger.info(f"Iteration {iteration + 1}")

            # Step 1: Ask LLM to select next tools
            if iteration == 0:
                # First iteration: just the query
                tool_selection_prompt = build_tool_selection_prompt(user_query)
            else:
                # Subsequent iterations: include previous results
                tool_selection_prompt = build_next_step_prompt(
                    user_query, all_tool_results
                )

            tool_selection_response = call_ollama(tool_selection_prompt)
            logger.info(f"Tool selection response: {tool_selection_response}")

            # Step 2: Parse tool calls
            tool_calls = parse_tool_calls(tool_selection_response)

            # Check if LLM says we're done (empty array or special marker)
            if not tool_calls:
                logger.info("LLM indicated no more tools needed")
                break

            logger.info(f"Parsed tool calls: {tool_calls}")
            all_tool_calls.extend(tool_calls)

            # Step 3: Execute tools
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            tool_results = loop.run_until_complete(execute_tools(tool_calls))
            loop.close()

            logger.info(f"Tool results: {tool_results}")
            all_tool_results.extend(tool_results)

            # Check if we got all the data we need
            # (if all results are search results with 0 count, we're done)
            all_empty_searches = all(
                r.get("result", {}).get("count") == 0
                for r in tool_results
                if r.get("tool") == "search_humans_by_name"
            )
            if all_empty_searches:
                logger.info("All searches returned 0 results, stopping")
                break

        # Step 4: Ask LLM to generate answer from all results
        answer_prompt = build_answer_prompt(user_query, all_tool_results)
        final_answer = call_ollama(answer_prompt)

        logger.info(f"Final answer: {final_answer}")

        # Return JSON response
        return jsonify({
            "query": user_query,
            "answer": final_answer,
            "debug": {
                "iterations": iteration + 1,
                "tool_calls": all_tool_calls,
                "tool_results": all_tool_results,
            }
        })

    except Exception as e:
        logger.error(f"AI search error: {e}", exc_info=True)
        return jsonify({
            "error": f"Search failed: {str(e)}",
            "query": user_query,
        }), 500
