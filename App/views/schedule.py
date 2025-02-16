from flask import Blueprint, render_template, jsonify
from flask_jwt_extended import jwt_required
from App.controllers.scheduler import help_desk_scheduler

schedule_views = Blueprint('schedule_views', __name__, template_folder='../templates')

@schedule_views.route('/schedule')
@jwt_required()
def schedule():
    return render_template('schedule/view.html')

@schedule_views.route('/api/generate_schedule', methods=['GET'])
@jwt_required()
def generate_schedule():
    try:
        # Call the scheduler with default parameters
        # I = 10 staff members
        # J = 45 shifts
        # K = 1 course (simplified for now)
        I, J, K = 10, 45, 1
        help_desk_scheduler(I, J, K)
        
        # For now return dummy data - will need to capture actual scheduler output
        schedule = [[0 for _ in range(J)] for _ in range(I)]
        
        return jsonify({
            'status': 'success',
            'schedule': schedule
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500