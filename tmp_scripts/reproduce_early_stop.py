
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
flask_mock = MagicMock()
flask_mock.session = {}
flask_mock.Blueprint = MagicMock()
flask_mock.render_template = MagicMock()
flask_mock.request = MagicMock()
flask_mock.jsonify = MagicMock()
flask_mock.globals = MagicMock()

sys.modules['flask'] = flask_mock
sys.modules['flask.globals'] = flask_mock.globals

# Set env vars
os.environ["AI_SEARCH_LLM_PROVIDER"] = "bedrock"
os.environ["AWS_REGION"] = "us-west-2"
os.environ["AI_SEARCH_BEDROCK_MODEL"] = "anthropic.claude-3-haiku-20240307-v1:0"

from blueprints.ai_chat import build_next_step_prompt, call_llm

def test_early_stop():
    print("\n--- Testing Early Stop Issue ---")
    query = "what was the most successful game for him ?"
    
    # Simulate result from Iteration 1 (Entity Extraction found Pavel)
    previous_results = [
        {
            "tool": "find_entities_by_name",
            "args": {"query": "pavel kletskov", "limit": 10},
            "result": [
                {"type": "human", "id": 117076, "name": "Pavel Kletskov", "similarity": 1.0}
            ],
            "elapsed_ms": 3402.85
        }
    ]
    
    prompt = build_next_step_prompt(query, previous_results)
    print(f"Prompt sent to LLM:\n{prompt[:500]}...\n")
    
    response, elapsed = call_llm(prompt)
    print(f"LLM Response ({elapsed:.2f}s):\n{response}")
    
    # Check if it calls a tool or returns empty array (stop)
    if "get_skater_game_stats" in response or "get_career_summary" in response:
        print("✅ SUCCESS: LLM called a stats tool.")
    elif "[]" in response or response.strip() == "":
        print("❌ FAILURE: LLM stopped early (returned empty array or nothing).")
    else:
        print("⚠️ UNKNOWN: Check response manually.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    try:
        test_early_stop()
    except Exception as e:
        print(f"Test failed: {e}")
