"""
================================================================================
Filename: constants.py
Description: Global constants for the application, including API endpoints, thresholds, and weights.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-08
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

# Backup Constants (v0.9.0)
BACKUP_RETENTION_COUNT = 14  # number of daily backups to keep

### Clash Royale Constants ###
# Inactivity thresholds (in days)
INACTIVE_DAYS = 7
VERY_INACTIVE_DAYS = 14
KICK_CANDIDATE_DAYS = 21

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


### Score Service Constants (v0.7.0 minimal) ###
DAYS_PER_RACE = 4
MAX_FAME_PER_DAY = 900  # 2 duel wins x 250 + 2 combat wins x 200
MAX_DECKS_PER_DAY = 4
MAX_FAME_PER_RACE = MAX_FAME_PER_DAY * DAYS_PER_RACE  # 3600
MAX_DECKS_PER_RACE = MAX_DECKS_PER_DAY * DAYS_PER_RACE  # 16

### Contribution Score Constants (v0.8.0) ###
# Component weights (sum to 1.0)
WAR_ACTIVITY_WEIGHT = 0.30
WAR_PERFORMANCE_WEIGHT = 0.20
CONTRIBUTION_DONATIONS_WEIGHT = 0.15
CONTRIBUTION_TROPHY_WEIGHT = 0.10
CONTRIBUTION_ACTIVITY_WEIGHT = 0.10
CONSISTENCY_WEIGHT = 0.10
SENIORITY_WEIGHT = 0.05

# Hill function parameters for activity calcul
ACTIVITY_HALF_LIFE = 7.0  # half-life: the number of days at which the score reaches 50.
ACTIVITY_STEEPNESS = 2.5  # steepness : controls how sharp the drop is.


# War Performance sub-component weights (sum to 1.0)
WAR_PERFORMANCE_FAME_WEIGHT = 0.40
WAR_PERFORMANCE_DECKS_WEIGHT = 0.30
WAR_PERFORMANCE_REPAIRS_WEIGHT = 0.20
WAR_PERFORMANCE_BOATS_WEIGHT = 0.10
WAR_PERFORMANCE_SUBMETRIC_CAP = (
    120  # cap each sub-metric (vs clan avg) before weighting
)

RECENT_RACES_WINDOW = 8  # races used for War Performance & Consistency components
DONATIONS_AVERAGE_WINDOW_DAYS = 30
MIN_RACES_FOR_CONSISTENCY = (
    3  # below this, Consistency uses the clan average of >3 races members
)

SENIORITY_DAYS_CAP = 365  # days after which Seniority maxes out at 100
TROPHY_PERCENTILE = 95  # percentile used to normalize Trophy Level

# Promotion / sanction rules
SANCTION_FAME_THRESHOLD = 1600
PROMOTION_BAND_TOP = 15
PROMOTION_BAND_ELDER = 25
PROMOTION_BAND_DEMOTE_COLEADER = 35
