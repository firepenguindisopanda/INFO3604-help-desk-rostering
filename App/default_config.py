SQLALCHEMY_DATABASE_URI="sqlite:///temp-database.db"
SECRET_KEY="secret key"
# CP-SAT solver time limit in seconds (default 60s)
CP_SAT_TIME_LIMIT = 240

# Scheduler Engine Configuration
# Options: 'pulp' (fairness-focused) or 'ortools' (coverage-focused)
SCHEDULER_ENGINE = 'ortools'

# Enable automatic fallback to OR-Tools if primary solver fails
# Set to False to disable fallback and fail fast
SCHEDULER_FALLBACK_ENABLED = True