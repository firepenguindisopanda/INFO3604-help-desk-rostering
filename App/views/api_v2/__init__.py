from flask import Blueprint

api_v2 = Blueprint('api_v2', __name__, url_prefix='/api/v2')

# NOTE: Additional admin assistant management routes are added in new modules.

# Import all endpoints to register them with the blueprint
from . import auth, admin, student, courses, schedule, performance, volunteer, assistant_admin

def register_api_v2(app):
    """Register the API v2 blueprint with the Flask app"""
    app.register_blueprint(api_v2)