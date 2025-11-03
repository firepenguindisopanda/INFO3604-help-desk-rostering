from flask import Blueprint

api_v2 = Blueprint('api_v2', __name__, url_prefix='/api/v2')

# NOTE: Additional admin assistant management routes are added in new modules.

# Import all endpoints to register them with the blueprint
# Following modular design principles - each module has single responsibility
from . import (
    auth, 
    admin, 
    student, 
    courses, 
    schedule, 
    schedule_config, 
    performance, 
    volunteer, 
    assistant_admin,
    requests,
    tracking,
    users,
    password_resets,
    registrations
)

def register_api_v2(app):
    """
    Register the API v2 blueprint with the Flask app
    
    Modular Design: All API v2 endpoints are registered through this single function
    Loose Coupling: App doesn't need to know about individual modules
    """
    app.register_blueprint(api_v2)