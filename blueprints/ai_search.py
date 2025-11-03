"""
AI-powered search blueprint using LLM (Ollama or AWS Bedrock Claude) and MCP tools.

This endpoint is accessible but not linked from other pages (testing only).
"""

import asyncio
import json
import logging
import os
from flask import Blueprint, render_template, request, jsonify
from hockey_blast_mcp.tools import get_all_tools

logger = logging.getLogger(__name__)

# Configuration: Choose LLM provider
LLM_PROVIDER = os.getenv("AI_SEARCH_LLM_PROVIDER", "ollama")  # "ollama" or "bedrock"
BEDROCK_REGION = os.getenv("AWS_REGION", "us-west-2")
BEDROCK_MODEL = os.getenv("AI_SEARCH_BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0")

ai_search_bp = Blueprint("ai_search", __name__)

# Tool registry - single source of truth from MCP tools package
TOOL_REGISTRY = get_all_tools()


def call_llm(prompt: str) -> str:
    """
    Call configured LLM provider (Ollama or AWS Bedrock).

    Args:
        prompt: User query

    Returns:
        LLM response as string
    """
    if LLM_PROVIDER == "bedrock":
        return call_bedrock_claude(prompt)
    else:
        return call_ollama(prompt)


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


def call_bedrock_claude(prompt: str) -> str:
    """
    Call AWS Bedrock with Claude model.

    Args:
        prompt: User query

    Returns:
        LLM response as string
    """
    import boto3

    try:
        bedrock = boto3.client(
            service_name="bedrock-runtime",
            region_name=BEDROCK_REGION
        )

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.0,  # Deterministic for tool selection
        }

        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL,
            body=json.dumps(request_body)
        )

        response_body = json.loads(response["body"].read())
        return response_body["content"][0]["text"]

    except Exception as e:
        logger.error(f"AWS Bedrock API error: {e}")
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
HOCKEY STATISTICS QUERY SYSTEM - ITERATION 1: ENTITY EXTRACTION

DATABASE CONTAINS:
- HUMANS: Players, goalies, referees, scorekeepers
- TEAMS: Hockey teams that compete
- ORGANIZATIONS: Leagues/venues (Sharks Ice, CAHA, etc.)
- GAMES: Individual game records with detailed statistics

MANDATORY TWO-PHASE QUERY PROCESSING:

Phase 1 (THIS ITERATION): Extract ALL entities mentioned in the query
Phase 2 (NEXT ITERATION): Use those entity IDs to answer the question

WHY TWO PHASES?
- Most queries have entities (WHO/WHERE) and questions (WHAT/HOW MANY)
- Entities provide context needed to answer questions
- Example: "goals by pavel" needs Pavel's ID before fetching goal stats

YOUR TASK FOR THIS ITERATION:
Identify and search for ALL entities mentioned in the query:
- Player/human names (first, last, nicknames)
- Team names (full names, nicknames like "good guys")
- Organization names (if mentioned)

ENTITY SEARCH TOOLS:
- find_entities_by_name(query, limit) - PRIMARY TOOL: Searches ALL sources (substring + semantic)
  * Searches humans AND teams simultaneously
  * Combines substring matching + AI fuzzy matching
  * Returns: [{{"type": "team"/"human", "id": int, "name": str, "similarity": float}}]
  * USE THIS FIRST for most queries
- semantic_search(query, entity_type, limit) - Secondary: AI-powered search for specific entity type
- search_humans_by_name(search_term, limit) - Secondary: Substring search for players only
- search_teams_by_name(search_term, limit) - Secondary: Substring search for teams only

WORKED EXAMPLES:

Example 1:
Query: "How many games has pavel kletskov played in sharks ice organization"
Iteration 1 (Entity Extraction):
[
  {{"tool": "find_entities_by_name", "args": {{"query": "pavel kletskov", "limit": 10}}}},
  {{"tool": "find_entities_by_name", "args": {{"query": "sharks ice", "limit": 5}}}}
]
→ Finds: Pavel Kletskov (human_id: 123), Sharks Ice (org_id: 1)

Example 2:
Query: "who scored most goals for good guys all time"
Iteration 1 (Entity Extraction):
[
  {{"tool": "find_entities_by_name", "args": {{"query": "good guys", "limit": 5}}}}
]
→ Finds: Good Guys (team_id: 708)

Example 3:
Query: "did good guys win any championships"
Iteration 1 (Entity Extraction):
[
  {{"tool": "find_entities_by_name", "args": {{"query": "good guys", "limit": 5}}}}
]
→ Finds: Good Guys (team_id: 708)

Example 4:
Query: "total number of goals in the database"
Iteration 1 (Entity Extraction):
[]
→ No entities mentioned

CURRENT QUERY: "{query}"

YOUR RESPONSE:
Return JSON array of entity search tool calls for ALL entities in this query.
If no entities mentioned, return empty array [].

Format: [{{"tool": "tool_name", "args": {{"param": value}}}}]"""

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

    prompt = f"""HOCKEY STATISTICS QUERY SYSTEM - ITERATION 2+: ANSWER THE QUESTION

ORIGINAL QUERY: "{user_query}"

ENTITIES FOUND IN ITERATION 1:
{results_summary}

YOUR TASK:
Now that we have entity IDs, use them to answer the original question.

AVAILABLE DATA RETRIEVAL TOOLS:

Team Player Data (CRITICAL FOR "WHO SCORED MOST" QUESTIONS):
- get_all_players_for_team(team_id) - Get ALL player IDs for a team
- get_org_skater_stats_batch(human_ids) - Get goal/assist/point stats for list of players (ACCEPTS LIST!)
  * Returns goals, assists, points, games_played for each player
  * Results sorted by goals descending (highest first)
  * USE THIS to answer "who scored most" questions!

Team Data:
- get_team_roster(team_id, limit) - Players sorted by games_played (NO goal stats!)
- get_team_stats(team_id) - Win/loss/championships
- get_team_by_id(team_id) - Basic team info

Human/Player Data (Single ID only):
- get_org_skater_stats(human_id) - Goals/assists/points/penalties for ONE player
- get_org_goalie_stats(human_id) - Saves/GAA/save percentage for ONE goalie
- get_org_human_stats(human_id) - Games played, roles for ONE human
- get_human_by_id(human_id) - Basic human info

Leaderboards:
- get_top_scorers(org_id, limit, min_games) - Top goal scorers org-wide
- get_top_by_stat(stat_name, org_id, limit) - Top performers in any stat

Game Data:
- get_skater_games(human_id, limit) - Games played as skater
- get_goalie_games(human_id, limit) - Games played as goalie

Comparisons:
- compare_two_skaters(human_id_1, human_id_2) - Head-to-head comparison

WORKED EXAMPLES (Iteration 2):

Example 1:
Query: "How many games has pavel kletskov played in sharks ice organization"
Previous Results: Pavel Kletskov (human_id: 123), Sharks Ice (org_id: 1)
Iteration 2:
[
  {{"tool": "get_org_human_stats", "args": {{"human_id": 123}}}}
]
→ Returns games_participated count

Example 2:
Query: "who scored most goals for good guys all time"
Previous Results: Good Guys (team_id: 708)
Iteration 2 Step 1:
[
  {{"tool": "get_all_players_for_team", "args": {{"team_id": 708}}}}
]
→ Returns list of all player IDs: [117076, 114087, 111913, ...]
Iteration 3 Step 2:
[
  {{"tool": "get_org_skater_stats_batch", "args": {{"human_ids": [117076, 114087, 111913]}}}}
]
→ Returns goal stats for all players, SORTED BY GOALS (highest first)

Example 3:
Query: "did good guys win any championships"
Previous Results: Good Guys (team_id: 708)
Iteration 2:
[
  {{"tool": "get_team_stats", "args": {{"team_id": 708}}}}
]
→ Returns championships_won count

Example 4:
Query: "who is the best performer in kletskov family"
Previous Results: Pavel Kletskov (human_id: 123), Andrei Kletskov (human_id: 456)
Iteration 2:
[
  {{"tool": "get_org_skater_stats", "args": {{"human_id": 123}}}},
  {{"tool": "get_org_skater_stats", "args": {{"human_id": 456}}}}
]
→ Returns stats for both, allowing comparison

CURRENT SITUATION:
- Query: "{user_query}"
- Entities found: See above
- What tool(s) will get the data to answer this question?

YOUR RESPONSE:
Return JSON array of tool calls needed to answer the question.
Return [] ONLY if you already have the complete answer data from iteration 1.

Format: [{{"tool": "tool_name", "args": {{"param": value}}}}]"""

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
    for i, call in enumerate(tool_calls):
        # Validate tool call format
        if not isinstance(call, dict):
            logger.error(f"Tool call {i} is not a dict: {call}")
            results.append({"error": f"Invalid tool call format: {call}"})
            continue

        if "tool" not in call:
            logger.error(f"Tool call {i} missing 'tool' key: {call}")
            results.append({"error": f"Missing tool name: {call}"})
            continue

        if "args" not in call:
            logger.error(f"Tool call {i} missing 'args' key: {call}")
            results.append({"error": f"Missing args for tool {call.get('tool')}: {call}"})
            continue

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
        completed_iterations = 0

        # Multi-step agentic loop (max 3 iterations, MINIMUM 2)
        for iteration in range(3):
            logger.info(f"Iteration {iteration + 1}")

            # Step 1: Ask LLM to select next tools
            if iteration == 0:
                # First iteration: entity extraction
                tool_selection_prompt = build_tool_selection_prompt(user_query)
            else:
                # Subsequent iterations: question answering
                tool_selection_prompt = build_next_step_prompt(
                    user_query, all_tool_results
                )

            tool_selection_response = call_llm(tool_selection_prompt)
            logger.info(f"Iteration {iteration + 1} - Tool selection response: {tool_selection_response}")

            # Step 2: Parse tool calls
            tool_calls = parse_tool_calls(tool_selection_response)
            logger.info(f"Iteration {iteration + 1} - Parsed tool calls: {tool_calls}")

            # Check if LLM says we're done (empty array)
            # BUT enforce minimum 2 iterations (entity extraction + question answering)
            if not tool_calls:
                if completed_iterations < 2:
                    # Must complete at least 2 iterations total
                    logger.info(f"Iteration {iteration + 1}: Empty tool calls but {completed_iterations} iterations completed, need minimum 2. Forcing continuation...")
                    # Force continuation by repeating the prompt with emphasis
                    continue
                else:
                    logger.info(f"Iteration {iteration + 1}: LLM indicated no more tools needed (after {completed_iterations} completed iterations)")
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

            # Track that we completed an iteration with actual work
            completed_iterations += 1

            # Check if all searches returned 0 results (entity not found)
            search_tools = [r for r in tool_results if "search" in r.get("tool", "").lower()]
            if search_tools:  # Only check if we actually did searches
                all_empty_searches = all(
                    r.get("result", {}).get("count") == 0
                    for r in search_tools
                )
                if all_empty_searches:
                    logger.info("All searches returned 0 results, stopping")
                    break

        # Step 4: Ask LLM to generate answer from all results
        answer_prompt = build_answer_prompt(user_query, all_tool_results)
        final_answer = call_llm(answer_prompt)

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
