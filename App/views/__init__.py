from .user import user_views
from .index import index_views
from .auth import auth_views
from .schedule import schedule_views
from .tracking import tracking_views
from .requests import requests_views
from .profile import profile_views
from .volunteer import volunteer_views 
from .notification import notification_views
from .performance import performance_bp

# All blueprints to be registered
views = [
    user_views,        # API endpoints for user management
    index_views,       # Root route and initialization
    auth_views,        # Authentication routes
    schedule_views,    # Schedule management
    tracking_views,    # Time tracking
    requests_views,    # Request management
    profile_views,     # User profiles
    volunteer_views,   # New volunteer views
    notification_views,
    performance_bp,    # Performance monitoring
]