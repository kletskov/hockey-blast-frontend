"""
Game utility functions for the Hockey Blast frontend.

This module contains shared utility functions for game-related operations,
ensuring consistency across different endpoints and blueprints.
"""

import re
from datetime import datetime, timedelta


def is_game_live(game, now=None):
    """
    Determine if a game is currently live.

    A game is considered live if BOTH conditions are met:
    1. Game status is "OPEN" (actively being played)
    2. Current time is within 75 minutes of game start

    Args:
        game: Game model instance with status, date, and time attributes
        now: Optional datetime object for current time (defaults to datetime.now())

    Returns:
        bool: True if the game is currently live, False otherwise

    Example:
        >>> game = Game(status="OPEN", date=date(2025, 12, 15), time=time(20, 0))
        >>> is_game_live(game)
        True  # If current time is within 75 minutes of 8:00 PM
    """
    if now is None:
        now = datetime.now()

    # Check if game status is OPEN
    if not game.status or game.status.upper() != "OPEN":
        return False

    # Check if game has valid date and time
    if not game.date or not game.time:
        return False

    # Calculate game datetime and 75-minute cutoff
    game_datetime = datetime.combine(game.date, game.time)
    game_live_cutoff = game_datetime + timedelta(minutes=75)

    # Game is live if current time is within the window
    return game_datetime <= now <= game_live_cutoff


def parse_live_time(live_time_str):
    """
    Parse a live_time string to extract period number and time left.

    Handles various time formats:
    - "Period 1, 1:10 left" -> period="1", time_left="1:10"
    - "Period 2, 48.8 left" -> period="2", time_left="48.8"
    - "Period 3, 0:48.8 left" -> period="3", time_left="0:48.8"
    - "Live" -> period="", time_left=""

    Args:
        live_time_str: String containing live game time information (e.g., "Period 2, 48.8 left")

    Returns:
        tuple: (period, time_left) where both are strings, empty strings if not found

    Example:
        >>> parse_live_time("Period 1, 1:10 left")
        ("1", "1:10")
        >>> parse_live_time("Period 2, 48.8 left")
        ("2", "48.8")
        >>> parse_live_time("Live")
        ("", "")
    """
    period = ""
    time_left = ""

    if not live_time_str:
        return period, time_left

    # Extract period number (e.g., "Period 1" -> "1")
    period_match = re.search(r'Period\s+(\d+)', live_time_str)
    if period_match:
        period = period_match.group(1)

    # Extract time left - handles "1:10 left", "48.8 left", "0:48.8 left", etc.
    time_match = re.search(r'([\d:.]+)\s+left', live_time_str)
    if time_match:
        time_left = time_match.group(1)

    return period, time_left
