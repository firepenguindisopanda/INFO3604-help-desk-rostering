from flask import Blueprint, render_template
from flask_jwt_extended import jwt_required

schedule_views = Blueprint('schedule_views', __name__, template_folder='../templates')

@schedule_views.route('/schedule')
@jwt_required()
def schedule():
    return render_template('schedule/view.html')