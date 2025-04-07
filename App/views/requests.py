from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for, send_from_directory
from flask_jwt_extended import jwt_required, current_user
from App.middleware import admin_required, volunteer_required
from App.controllers.request import (
    get_all_requests,
    get_student_requests,
    approve_request,
    reject_request,
    create_student_request,
    cancel_request,
    get_available_shifts_for_student,
    get_available_replacements
)
from App.controllers.registration import (
    get_all_registration_requests,
    approve_registration,
    reject_registration
)
import os
from datetime import datetime

requests_views = Blueprint('requests_views', __name__, template_folder='../templates')

# Remove the old datetime filter to avoid conflicts
# The filter is now registered globally in main.py

# ADMIN ROUTES
@requests_views.route('/requests')
@jwt_required()
@admin_required
def requests():
    """Admin view for managing all shift requests"""
    # Get all requests from the database
    tutors = get_all_requests()
    return render_template('admin/requests/index.html', tutors=tutors)
    
@requests_views.route('/registrations')
@jwt_required()
@admin_required
def registrations():
    """Admin view for managing registration requests"""
    # Get all registration requests
    registration_data = get_all_registration_requests()
    
    # No need to register the filter here anymore
    # It's now registered globally in main.py
    
    return render_template('admin/requests/registrations.html', 
                           pending_registrations=registration_data['pending'],
                           approved_registrations=registration_data['approved'],
                           rejected_registrations=registration_data['rejected'])

@requests_views.route('/api/requests/<int:request_id>/approve', methods=['POST'])
@jwt_required()
@admin_required
def approve_request_endpoint(request_id):
    """API endpoint to approve a request"""
    success, message = approve_request(request_id)
    
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
        
    return jsonify({
        "success": success,
        "message": message
    })

@requests_views.route('/api/requests/<int:request_id>/reject', methods=['POST'])
@jwt_required()
@admin_required
def reject_request_endpoint(request_id):
    """API endpoint to reject a request"""
    success, message = reject_request(request_id)
    
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
        
    return jsonify({
        "success": success,
        "message": message
    })

# VOLUNTEER/STUDENT ROUTES
@requests_views.route('/volunteer/requests')
@jwt_required()
@volunteer_required
def volunteer_requests():
    """Student/volunteer view for managing their own requests"""
    # Get the current user's requests
    username = current_user.username
    requests_list = get_student_requests(username)
    
    # Categorize by status
    pending_requests = [r for r in requests_list if r['status'] == 'PENDING']
    approved_requests = [r for r in requests_list if r['status'] == 'APPROVED']
    rejected_requests = [r for r in requests_list if r['status'] == 'REJECTED']
    
    # Get available shifts for new requests
    available_shifts = get_available_shifts_for_student(username)
    
    # Get available replacements
    available_replacements = get_available_replacements(username)
    
    return render_template('volunteer/requests/index.html',
                          pending_requests=pending_requests,
                          approved_requests=approved_requests,
                          rejected_requests=rejected_requests,
                          available_shifts=available_shifts,
                          available_replacements=available_replacements)

@requests_views.route('/volunteer/submit_request', methods=['POST'])
@jwt_required()
@volunteer_required
def submit_request():
    """Submit a new shift change request"""
    data = request.form
    
    # Extract data from form
    shift_id = data.get('shiftToChange')
    reason = data.get('reasonForChange')
    replacement = data.get('proposedReplacement')
    
    # Validate required fields
    if not shift_id or not reason:
        flash("Shift and reason are required fields", "error")
        return redirect(url_for('requests_views.volunteer_requests'))
    
    # Create the request
    success, message = create_student_request(
        current_user.username,
        shift_id,
        reason,
        replacement
    )
    
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
        
    return redirect(url_for('requests_views.volunteer_requests'))

@requests_views.route('/volunteer/cancel_request/<int:request_id>', methods=['POST'])
@jwt_required()
@volunteer_required
def cancel_request_endpoint(request_id):
    """Cancel a pending request"""
    success, message = cancel_request(request_id, current_user.username)
    
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
        
    return redirect(url_for('requests_views.volunteer_requests'))

# API Routes for both admin and volunteer
@requests_views.route('/api/requests', methods=['GET'])
@jwt_required()
def get_requests_api():
    """API endpoint to get requests based on user role"""
    if current_user.is_admin():
        # Admin gets all requests
        tutors = get_all_requests()
        all_requests = []
        for tutor in tutors:
            all_requests.extend(tutor['requests'])
        return jsonify(all_requests)
    else:
        # Students get only their own requests
        requests_list = get_student_requests(current_user.username)
        return jsonify(requests_list)
        
@requests_views.route('/api/registrations/<int:registration_id>/approve', methods=['POST'])
@jwt_required()
@admin_required
def approve_registration_endpoint(registration_id):
    """API endpoint to approve a registration request"""
    success, message = approve_registration(registration_id, current_user.username)
    
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
        
    return jsonify({
        "success": success,
        "message": message
    })

@requests_views.route('/api/registrations/<int:registration_id>/reject', methods=['POST'])
@jwt_required()
@admin_required
def reject_registration_endpoint(registration_id):
    """API endpoint to reject a registration request"""
    success, message = reject_registration(registration_id, current_user.username)
    
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
        
    return jsonify({
        "success": success,
        "message": message
    })
    
@requests_views.route('/registrations/download/<int:registration_id>', methods=['GET'])
@jwt_required()
@admin_required
def download_transcript(registration_id):
    """Download a transcript file for a registration request"""
    from App.models import RegistrationRequest
    import os
    
    registration = RegistrationRequest.query.get(registration_id)
    if not registration or not registration.transcript_path:
        flash("Transcript not found", "error")
        return redirect(url_for('requests_views.registrations'))
    
    # Extract filename from path
    filename = os.path.basename(registration.transcript_path)
    
    # The files are saved in uploads/transcripts, not App/uploads/transcripts
    directory = os.path.join('uploads', 'transcripts')
    
    # Return the file
    return send_from_directory(directory, filename)

@requests_views.route('/api/available-shifts', methods=['GET'])
@jwt_required()
@volunteer_required
def get_available_shifts_api():
    """API endpoint to get available shifts for the current student"""
    available_shifts = get_available_shifts_for_student(current_user.username)
    return jsonify(available_shifts)

@requests_views.route('/api/available-replacements', methods=['GET'])
@jwt_required()
@volunteer_required
def get_available_replacements_api():
    """API endpoint to get available replacement assistants"""
    available_replacements = get_available_replacements(current_user.username)
    return jsonify(available_replacements)