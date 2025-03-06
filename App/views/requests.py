from flask import Blueprint, render_template, jsonify, request
from flask_jwt_extended import jwt_required, current_user
from App.middleware import admin_required

requests_views = Blueprint('requests_views', __name__, template_folder='../templates')

@requests_views.route('/requests')
@jwt_required()
@admin_required
def requests():
    # Mock data for tutors with their requests
    tutors = [
        {
            "id": 1,
            "name": "John Doe",
            "role": "Tutor",
            "id_number": "816031882",
            "image": "/api/placeholder/48/48",
            "requests": [
                {
                    "id": 101,
                    "date": "October 1, 2024",
                    "time_slot": "10:00 AM - 11:00 AM",
                    "reason": "Need to attend a doctor's appointment",
                    "status": "pending"
                },
                {
                    "id": 102,
                    "date": "September 25, 2024",
                    "time_slot": "2:00 PM - 3:00 PM",
                    "reason": "Family emergency",
                    "status": "approved"
                }
            ]
        },
        {
            "id": 2,
            "name": "Sam Rico",
            "role": "Tutor",
            "id_number": "816031873",
            "image": "/api/placeholder/48/48",
            "requests": [
                {
                    "id": 201,
                    "date": "October 3, 2024",
                    "time_slot": "11:00 AM - 12:00 PM",
                    "reason": "Academic conference",
                    "status": "pending"
                }
            ]
        },
        {
            "id": 3,
            "name": "Taylor Swift",
            "role": "Student Assistant",
            "id_number": "816031874",
            "image": "/api/placeholder/48/48",
            "requests": []
        },
        {
            "id": 4,
            "name": "Josh Zack",
            "role": "Student Assistant",
            "id_number": "816031875",
            "image": "/api/placeholder/48/48",
            "requests": [
                {
                    "id": 401,
                    "date": "September 28, 2024",
                    "time_slot": "9:00 AM - 10:00 AM",
                    "reason": "Exam preparation",
                    "status": "rejected"
                },
                {
                    "id": 402,
                    "date": "October 5, 2024",
                    "time_slot": "3:00 PM - 4:00 PM",
                    "reason": "Group project meeting",
                    "status": "pending"
                }
            ]
        }
    ]
    
    return render_template('admin/requests/index.html', tutors=tutors)

@requests_views.route('/api/requests/<int:request_id>/approve', methods=['POST'])
@jwt_required()
@admin_required
def approve_request(request_id):
    
    try:
        
        return jsonify({
            "success": True,
            "message": f"Request #{request_id} approved successfully"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error approving request: {str(e)}"
        }), 400

@requests_views.route('/api/requests/<int:request_id>/reject', methods=['POST'])
@jwt_required()
@admin_required
def reject_request(request_id):

    try:
        
        return jsonify({
            "success": True,
            "message": f"Request #{request_id} rejected successfully"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error rejecting request: {str(e)}"
        }), 400