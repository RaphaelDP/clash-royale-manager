"""
================================================================================
Filename: constants.py
Description: Global constants for the application, including API endpoints, thresholds, and weights.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-07-10
Version: 0.2.3
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

### Clan Health Score Constants (v0.6.0) ###
# Targets used to normalize Clan Health Score components
EXPECTED_FAME_PER_PLAYER = (
    3000  # War Efficiency target (avg fame per player, last race)
)
DONATION_TARGET = 150  # Donations target (weekly)
GROWTH_TARGET_TROPHIES = 200  # Growth target (trophy gain over GROWTH_WINDOW_DAYS)

# Weights for each component of the Clan Health Score
CLAN_HEALTH_WEIGHTS = {
    "activity": 0.25,
    "war_participation": 0.20,
    "war_efficiency": 0.15,
    "donations": 0.10,
    "retention": 0.10,
    "growth": 0.10,
    "leadership": 0.0,  # for now, leadership is not considered in the Clan Health Score calculation
    "inactivity": 0.1,
}

# Time windows (in days)
RETENTION_WINDOW_DAYS = 30
RETENTION_WINDOW_TOLERANCE_DAYS = 5
GROWTH_WINDOW_DAYS = 30

# Activity score buckets: (days_since_last_seen, score).
# Values between day 30 and day 60 are linearly interpolated to avoid a
# hard cliff; other gaps snap to the lower threshold's score (step function).
ACTIVITY_SCORE_BUCKETS = [
    (0, 100),
    (1, 98),
    (2, 96),
    (3, 94),
    (7, 80),
    (14, 55),
    (30, 20),
    (60, 0),
]

### Score Service Constants (v0.7.0 minimal) ###
# Theoretical max fame achievable in a single river race:
# 4 days x (2 duel wins x 250 + 2 combat wins x 200) = 4 x 900 = 3600
MAX_FAME_PER_RACE = 3600
