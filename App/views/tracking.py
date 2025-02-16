from flask import Blueprint, render_template
from flask_jwt_extended import jwt_required

tracking_views = Blueprint('tracking_views', __name__, template_folder='../templates')

@tracking_views.route('/timeTracking')
@jwt_required()
def time_tracking():
    return render_template('tracking/index.html')