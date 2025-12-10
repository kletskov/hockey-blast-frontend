
import os
import sys
import json
import logging

# Add project root to path
sys.path.append(os.path.abspath("hockey-blast-frontend"))
sys.path.append(os.path.abspath("hockey-blast-mcp"))
sys.path.append(os.path.abspath("hockey-blast-common-lib"))

# Mock Flask session
from unittest.mock import MagicMock
import sys

# Create a mock flask module that behaves like a package
flask_mock = MagicMock()
flask_mock.session = {}
flask_mock.Blueprint = MagicMock()
flask_mock.render_template = MagicMock()
flask_mock.request = MagicMock()
flask_mock.jsonify = MagicMock()
flask_mock.globals = MagicMock() # For flask_sqlalchemy

sys.modules['flask'] = flask_mock
sys.modules['flask.globals'] = flask_mock.globals

# Import the functions we need to test
# We need to manually set the env vars first because they are read at module level
os.environ["AI_SEARCH_LLM_PROVIDER"] = "bedrock"
os.environ["AWS_REGION"] = "us-west-2"
os.environ["AI_SEARCH_BEDROCK_MODEL"] = "anthropic.claude-3-haiku-20240307-v1:0"

from blueprints.ai_chat import build_tool_selection_prompt, build_answer_prompt, call_llm

def test_entity_extraction():
    print("\n--- Testing Entity Extraction (Hallucination Check) ---")
    query = "how long pavel plays for"
    print(f"Query: {query}")
    
    prompt = build_tool_selection_prompt(query)
    # print(f"Prompt:\n{prompt[:500]}...\n")
    
    response, elapsed = call_llm(prompt)
    print(f"LLM Response ({elapsed:.2f}s):\n{response}")
    
    # Check if it hallucinated an ID or correctly called a search tool
    if "123" in response and "find_entities_by_name" not in response:
        print("❌ FAILURE: Hallucinated ID 123 without search.")
    elif "find_entities_by_name" in response:
        print("✅ SUCCESS: Called search tool.")
    else:
        print("⚠️ UNCERTAIN: Check response manually.")

def test_answer_generation_links():
    print("\n--- Testing Answer Generation (Link Check) ---")
    query = "which game did he get most points ?"
    
    # Simulated tool results (from previous context)
    tool_results = [
        {
            "tool": "get_skater_game_stats",
            "args": {"human_id": 117076, "sort_by": "points", "limit": 1},
            "result": {
                "best_game": {
                    "game_id": 247477,
                    "date": "2018-06-30",
                    "team_name": "Icequakes",
                    "goals": 1,
                    "assists": 6,
                    "points": 7,
                    "penalty_minutes": 3,
                    "game_link": "[Game 247477](https://hockey-blast.com/game_card?game_id=247477)" # Simulated link presence
                }
            }
        }
    ]
    
    prompt = build_answer_prompt(query, tool_results)
    response, elapsed = call_llm(prompt)
    print(f"LLM Response ({elapsed:.2f}s):\n{response}")
    
    if "https://hockey-blast.com/game_card" in response:
        print("✅ SUCCESS: Link included.")
    else:
        print("❌ FAILURE: Link missing.")

if __name__ == "__main__":
    # Configure logging to avoid noise
    logging.basicConfig(level=logging.ERROR)
    
    try:
        test_entity_extraction()
        test_answer_generation_links()
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
