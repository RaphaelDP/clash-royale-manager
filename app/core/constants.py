"""
================================================================================
Filename: constants.py
Description: Global constants for the application, including API endpoints, thresholds, and weights.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-06
Version: 0.2.1
Python Version: 3.11
Dependencies: None
================================================================================
"""

### Global Constants ###
# Clash Royale API
CR_API_BASE_URL = "https://api.clashroyale.com/v1"
DEFAULT_TIMEOUT = 10
CACHE_EXPIRATION = 300  # Cache expiration time in seconds
MAX_RETRIES = 3

CACHE_NAME = "cr_cache"


### Clash Royale Constants ###
# Inactivity thresholds (in days)
INACTIVE_DAYS = 7
VERY_INACTIVE_DAYS = 14
KICK_CANDIDATE_DAYS = 21

# Promotion score weights
WAR_ACTIVITY_WEIGHT = 0.4
WAR_WIN_RATE_WEIGHT = 0.3
DONATIONS_WEIGHT = 0.2
TROPHY_LEVEL_WEIGHT = 0.1

# Kick score thresholds
KICK_SCORE_INACTIVE = 50
KICK_SCORE_MISSED_WARS = 30
KICK_SCORE_NO_DONATIONS = 20
