"""
AI-powered chat blueprint with conversation support.

This blueprint provides a ChatGPT-like interface where users can have
multi-turn conversations with context preservation.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session
from hockey_blast_mcp.tools import get_all_tools

logger = logging.getLogger(__name__)

# Configuration: Choose LLM provider
LLM_PROVIDER = os.getenv("AI_SEARCH_LLM_PROVIDER", "ollama")  # "ollama" or "bedrock"
BEDROCK_REGION = os.getenv("AWS_REGION", "us-west-2")
BEDROCK_MODEL = os.getenv("AI_SEARCH_BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0")
MAX_HISTORY_MESSAGES = 10  # Keep last N message pairs for context

ai_chat_bp = Blueprint("ai_chat", __name__)

# Tool registry - single source of truth from MCP tools package
TOOL_REGISTRY = get_all_tools()


def get_conversation_history():
    """
    Get conversation history from session.

    Returns:
        List of message dictionaries with role, content, timestamp
    """
    if 'conversation' not in session:
        session['conversation'] = []
    return session['conversation']


def add_to_conversation(role: str, content: str, debug: dict = None):
    """
    Add a message to the conversation history.

    Args:
        role: "user" or "assistant"
        content: Message content
        debug: Optional debug information (for assistant messages)
    """
    conversation = get_conversation_history()
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if debug:
        message["debug"] = debug
    conversation.append(message)

    # Limit history to prevent token overflow
    if len(conversation) > MAX_HISTORY_MESSAGES * 2:  # *2 because user+assistant pairs
        # Keep system prompt if exists, plus last N pairs
        session['conversation'] = conversation[-(MAX_HISTORY_MESSAGES * 2):]
    else:
        session['conversation'] = conversation

    session.modified = True


def clear_conversation():
    """Clear conversation history from session."""
    session['conversation'] = []
    session.modified = True


def format_conversation_for_llm(conversation: list, current_query: str) -> str:
    """
    Format conversation history for LLM context.

    Args:
        conversation: List of previous messages
        current_query: Current user question

    Returns:
        Formatted string with conversation history
    """
    if not conversation:
        return current_query

    # Build conversation context
    history_text = "CONVERSATION HISTORY:\n"
    for msg in conversation[-MAX_HISTORY_MESSAGES * 2:]:  # Last N pairs
        role_label = "User" if msg["role"] == "user" else "Assistant"
        history_text += f"{role_label}: {msg['content']}\n"

    history_text += f"\nCURRENT QUESTION: {current_query}\n"
    return history_text


def call_llm(prompt: str, conversation_history: list = None, system_prompt: str = None) -> tuple:
    """
    Call configured LLM provider (Ollama or AWS Bedrock).

    Args:
        prompt: User query
        conversation_history: List of previous messages with role and content
        system_prompt: Optional system instruction (for Bedrock)

    Returns:
        Tuple of (LLM response as string, elapsed time in seconds)
    """
    start_time = time.time()

    if LLM_PROVIDER == "bedrock":
        response = call_bedrock_claude(prompt, conversation_history, system_prompt)
    else:
        # Ollama doesn't support message arrays, so format as text
        if conversation_history:
            formatted_history = format_conversation_for_llm(conversation_history, prompt)
            full_prompt = system_prompt + "\n\n" + formatted_history if system_prompt else formatted_history
            response = call_ollama(full_prompt)
        else:
            response = call_ollama(system_prompt + "\n\n" + prompt if system_prompt else prompt)

    elapsed = time.time() - start_time
    return response, elapsed


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


def call_bedrock_claude(prompt: str, conversation_history: list = None, system_prompt: str = None) -> str:
    """
    Call AWS Bedrock with Claude model.

    Args:
        prompt: Current user query
        conversation_history: List of previous messages with role and content
        system_prompt: Optional system instruction (separate from conversation)

    Returns:
        LLM response as string
    """
    import boto3

    try:
        bedrock = boto3.client(
            service_name="bedrock-runtime",
            region_name=BEDROCK_REGION
        )

        # Build messages array from conversation history
        messages = []
        if conversation_history:
            for msg in conversation_history:
                # Only include user and assistant messages (skip any with debug info)
                if msg["role"] in ["user", "assistant"]:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

        # Add current prompt as user message
        messages.append({
            "role": "user",
            "content": prompt
        })

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": messages,
            "temperature": 0.0,  # Deterministic for tool selection
        }

        # Add system prompt if provided
        if system_prompt:
            request_body["system"] = system_prompt

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
        user_query: Original user question (may include conversation context)

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

**IMPORTANT: HANDLING CONVERSATION CONTEXT**
If the query includes CONVERSATION HISTORY, you MUST:
1. Read the conversation history to understand what entities were previously discussed
2. Look for pronouns/references in the CURRENT QUESTION (like "them", "their", "his", "the team", etc.)
3. If the current question references previous entities, search for those SAME entities again
4. Example:
   - Previous: "goalies for goon friends"
   - Current: "what about best skater for them"
   - Action: Search for "goon friends" again because "them" refers to those teams

YOUR TASK FOR THIS ITERATION:
Identify and search for ALL entities mentioned in the query (including referenced entities from history):
- Player/human names (first, last, nicknames)
- Team names (full names, nicknames like "good guys", "goon friends")
- Organization names (if mentioned)
- Pronouns that refer to entities in conversation history

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

YOUR RESPONSE:
Return JSON array of entity search tool calls for ALL entities in this query.
If no entities mentioned, return empty array [].

Format: [{{"tool": "tool_name", "args": {{"param": value}}}}]"""

    return tools_description


def build_next_step_prompt(user_query: str, previous_results: list) -> str:
    """
    Build prompt for LLM to select next tools based on previous results.

    Args:
        user_query: Original user question (may include conversation context)
        previous_results: Results from previous tool executions

    Returns:
        Formatted prompt for next tool selection
    """
    results_summary = json.dumps(previous_results, indent=2)

    prompt = f"""HOCKEY STATISTICS QUERY SYSTEM - ITERATION 2+: ANSWER THE QUESTION

ENTITIES FOUND IN ITERATION 1:
{results_summary}

YOUR TASK:
Now that we have entity IDs, use them to answer the original question.

AVAILABLE DATA RETRIEVAL TOOLS:

Team Player Data (CRITICAL FOR "WHO SCORED MOST FOR TEAM X" QUESTIONS):
- get_all_players_for_teams(team_ids) - Get ALL player IDs for one or more teams
- get_org_skater_team_stats_batch(human_ids, team_id) - **CRITICAL: USE THIS for team-specific scoring queries!**
  * Returns goals/assists/points SCOPED TO A SPECIFIC TEAM (not all-time!)
  * Results sorted by goals descending (highest first)
  * REQUIRED when query mentions "for team X" or "while on team Y"
  * Example: "who scored most for Good Guys" → use this with team_id=708
- get_org_skaters_stats(human_ids) - All-time stats across ALL teams (use only for career totals!)
  * DO NOT use for team-specific queries
  * Only use when question asks about "career", "all-time", or doesn't mention specific team

Team Data:
- get_teams_rosters(team_ids, limit) - Players sorted by games_played (NO goal stats!)
- get_teams_stats(team_ids) - Win/loss/championships
- get_teams_by_ids(team_ids) - Basic team info

Human/Player Data:
- get_org_skaters_stats(human_ids) - Goals/assists/points/penalties (batch capable)
- get_org_goalies_stats(human_ids) - Saves/GAA/save percentage (batch capable)
- get_org_humans_stats(human_ids) - Games played, roles (batch capable)
- get_humans_by_ids(human_ids) - Basic human info (batch capable)
- get_teams_for_human(human_id) - **USE FOR "WHAT TEAMS" QUERIES!** Get all teams a player has played for
  * Returns team roster history with games_played, roles (G/C/A/S), date ranges
  * REQUIRED when query asks "what teams", "which teams", "where did X play", "team history"
  * Example: "what teams did pavel play for" → use this with human_id

Leaderboards:
- get_top_scorers(org_id, limit, min_games) - Top goal scorers org-wide
- get_top_by_stat(stat_name, org_id, limit) - Top performers in any stat

Game Data:
- get_skaters_games(human_ids, limit) - Games played as skater (batch capable)
- get_goalies_games(human_ids, limit) - Games played as goalie (batch capable)
- get_games_details(game_ids) - Get game info (teams, scores, date, time, status) for specific games
- get_games_goals(game_ids) - Get all goals scored in specific games (who scored, assists, period)
- get_games_rosters(game_ids, team_id) - Get all players who played in specific games
- get_player_game_performance(human_id, game_id) - **CRITICAL: USE THIS to get what a specific player did in a specific game!**
  * Returns goals, assists, penalties, role, team, game context for ONE player in ONE game
  * REQUIRED when you know both player ID and game ID and want performance details
  * Example: "what did Pavel do in his last game" → get last game ID, then use this tool
  * Provides rich narrative detail instead of just "Last game" link

Game Search/Statistics (USE THESE for aggregate game queries):
- get_highest_scoring_games(limit, org_id) - **CRITICAL: USE THIS for "highest scoring game", "most goals in a game", "game with most goals"!**
  * Returns games sorted by total goal count (descending)
  * NO NEED to search for entities first - this is a direct statistical query
  * Example: "what game has most goals ever" → use this with limit=10
  * Example: "highest scoring game" → use this with limit=1
- get_recent_games(limit, org_id, status) - Get most recent games by date
  * Returns games sorted by date (most recent first)
  * Optional status filter: "Final", "OPEN", "Scheduled"
  * Example: "recent games" → use this with limit=20
  * Example: "latest completed games" → use this with status="Final"

Comparisons:
- compare_two_skaters(human_id_1, human_id_2) - Head-to-head comparison

WORKED EXAMPLES (Iteration 2):

Example 1:
Query: "How many games has pavel kletskov played in sharks ice organization"
Previous Results: Pavel Kletskov (human_id: 123), Sharks Ice (org_id: 1)
Iteration 2:
[
  {{"tool": "get_org_humans_stats", "args": {{"human_ids": 123}}}}
]
→ Returns games_participated count

Example 2:
Query: "who scored most goals for good guys all time"
Previous Results: Good Guys (team_id: 708)
Iteration 2 Step 1:
[
  {{"tool": "get_all_players_for_teams", "args": {{"team_ids": 708}}}}
]
→ Returns list of all player IDs: [117076, 114087, 111913, ...]
Iteration 3 Step 2:
[
  {{"tool": "get_org_skater_team_stats_batch", "args": {{"human_ids": [117076, 114087, 111913], "team_id": 708}}}}
]
→ Returns goal stats for all players WHILE ON THIS TEAM, SORTED BY GOALS (highest first)

Example 3:
Query: "did good guys win any championships"
Previous Results: Good Guys (team_id: 708)
Iteration 2:
[
  {{"tool": "get_teams_stats", "args": {{"team_ids": 708}}}}
]
→ Returns championships_won count

Example 4:
Query: "who is the best performer in kletskov family"
Previous Results: Pavel Kletskov (human_id: 123), Andrei Kletskov (human_id: 456)
Iteration 2:
[
  {{"tool": "get_org_skaters_stats", "args": {{"human_ids": [123, 456]}}}}
]
→ Returns stats for both in single call, allowing comparison

YOUR RESPONSE:
Return JSON array of tool calls needed to answer the question.
Return [] ONLY if you already have the complete answer data from iteration 1.

Format: [{{"tool": "tool_name", "args": {{"param": value}}}}]"""

    return prompt


def build_answer_prompt(user_query: str, tool_results: list) -> str:
    """
    Build prompt for LLM to generate final answer from tool results.

    Args:
        user_query: Original user question (may include conversation context)
        tool_results: List of tool execution results

    Returns:
        Formatted prompt for answer generation
    """
    results_json = json.dumps(tool_results, indent=2)

    prompt = f"""You are a helpful hockey statistics assistant.

I executed these tools and got the following data:

{results_json}

IMPORTANT INSTRUCTIONS:
1. Provide a clear, concise answer to the user's question based on this data.
2. Format numbers appropriately (e.g., "0.50 goals per game" not "0.5").
3. If the data shows the user wasn't found or has no stats, say so politely.
4. **CRITICAL - ENTITY LINKING**: When you mention ANY entity, you MUST copy the link from the data EXACTLY as shown:

   EXAMPLE:
   If the data contains: "human_link": "[Pavel Kletskov](https://hockey-blast.com/skater_performance/?human_id=117076)"
   Then write: "[Pavel Kletskov](https://hockey-blast.com/skater_performance/?human_id=117076) has 292 goals..."

   NOT: "Pavel Kletskov has 292 goals..."  (WRONG - missing link!)

   - For players: Copy the ENTIRE "human_link" value exactly
   - For teams: Copy the ENTIRE "team_link" value exactly
   - For games: Copy the ENTIRE "first_game_link" or "last_game_link" or "game_link" value exactly
   - These are pre-formatted markdown links - copy them character-for-character
   - ALWAYS include the link when mentioning the entity name

Answer:"""

    return prompt


async def execute_tool(tool_name: str, args: dict) -> dict:
    """
    Execute a single MCP tool with timing.

    Args:
        tool_name: Name of tool to execute
        args: Tool arguments

    Returns:
        Tool result dictionary with timing info
    """
    if tool_name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool: {tool_name}", "elapsed_ms": 0}

    start_time = time.time()
    try:
        tool_func = TOOL_REGISTRY[tool_name]
        result = await tool_func(**args)
        elapsed_ms = (time.time() - start_time) * 1000
        return {"tool": tool_name, "args": args, "result": result, "elapsed_ms": round(elapsed_ms, 2)}
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(f"Tool execution error: {tool_name} - {e}")
        return {"tool": tool_name, "args": args, "error": str(e), "elapsed_ms": round(elapsed_ms, 2)}


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


@ai_chat_bp.route("/ai-chat", methods=["GET"])
def chat_ui():
    """
    Render chat interface.
    """
    return render_template("ai_chat.html")


@ai_chat_bp.route("/ai-chat/message", methods=["POST"])
def send_message():
    """
    Process a chat message with conversation context.

    POST body: {"message": "user question"}
    Returns: {"role": "assistant", "content": "answer", "debug": {...}}
    """
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Please provide a message"}), 400

    try:
        request_start_time = time.time()
        print(f"\n====== AI Chat Message: {user_message} ======")

        # Add user message to conversation
        add_to_conversation("user", user_message)

        # Get conversation history (exclude current message for context)
        conversation = get_conversation_history()
        conversation_context = conversation[:-1]  # All messages before current

        print(f"Conversation history length: {len(conversation_context)}")
        if conversation_context:
            print(f"Last context message role: {conversation_context[-1].get('role')}")
            print(f"Last context message content preview: {conversation_context[-1].get('content')[:100] if len(conversation_context[-1].get('content', '')) > 100 else conversation_context[-1].get('content')}")
        else:
            print("No conversation history - this is the first message")

        all_tool_calls = []
        all_tool_results = []
        completed_iterations = 0
        llm_timings = []  # Track LLM call times

        # Multi-step agentic loop (max 5 iterations, MINIMUM 2)
        for iteration in range(5):
            logger.info(f"Iteration {iteration + 1}")

            # Step 1: Ask LLM to select next tools
            if iteration == 0:
                # First iteration: entity extraction
                # Use tool selection prompt as system instruction
                system_instructions = build_tool_selection_prompt(user_message)
                # For Bedrock: pass conversation history + current query
                # The system instructions are separate
                tool_selection_response, llm_time = call_llm(
                    user_message,
                    conversation_history=conversation_context,
                    system_prompt=system_instructions
                )
                llm_timings.append({"iteration": iteration + 1, "phase": "tool_selection", "time_ms": round(llm_time * 1000, 2)})
            else:
                # Subsequent iterations: question answering
                # Build prompt with tool results
                system_instructions = build_next_step_prompt(user_message, all_tool_results)
                tool_selection_response, llm_time = call_llm(
                    user_message,
                    conversation_history=conversation_context,
                    system_prompt=system_instructions
                )
                llm_timings.append({"iteration": iteration + 1, "phase": "tool_selection", "time_ms": round(llm_time * 1000, 2)})

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
        answer_system_prompt = build_answer_prompt(user_message, all_tool_results)
        final_answer, llm_time = call_llm(
            user_message,
            conversation_history=conversation_context,
            system_prompt=answer_system_prompt
        )
        llm_timings.append({"iteration": "final", "phase": "answer_generation", "time_ms": round(llm_time * 1000, 2)})

        logger.info(f"Final answer: {final_answer}")

        # Calculate total time
        total_time_ms = round((time.time() - request_start_time) * 1000, 2)
        total_llm_time_ms = round(sum(t["time_ms"] for t in llm_timings), 2)
        total_tool_time_ms = round(sum(r.get("elapsed_ms", 0) for r in all_tool_results), 2)

        # Add assistant response to conversation
        debug_info = {
            "iterations": iteration + 1,
            "tool_calls": all_tool_calls,
            "tool_results": all_tool_results,
            "timing": {
                "total_ms": total_time_ms,
                "llm_total_ms": total_llm_time_ms,
                "llm_calls": llm_timings,
                "tools_total_ms": total_tool_time_ms,
            }
        }
        add_to_conversation("assistant", final_answer, debug_info)

        # Return JSON response
        return jsonify({
            "role": "assistant",
            "content": final_answer,
            "timestamp": datetime.utcnow().isoformat(),
            "debug": debug_info
        })

    except Exception as e:
        logger.error(f"AI chat error: {e}", exc_info=True)
        return jsonify({
            "error": f"Chat failed: {str(e)}",
            "message": user_message,
        }), 500


@ai_chat_bp.route("/ai-chat/history", methods=["GET"])
def get_history():
    """
    Get conversation history.

    Returns: {"messages": [...]}
    """
    conversation = get_conversation_history()
    return jsonify({"messages": conversation})


@ai_chat_bp.route("/ai-chat/clear", methods=["POST"])
def clear_chat():
    """
    Clear conversation history.

    Returns: {"status": "cleared"}
    """
    clear_conversation()
    return jsonify({"status": "cleared"})
