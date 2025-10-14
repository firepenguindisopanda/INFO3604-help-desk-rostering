import mimetypes

from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for, send_file, current_app
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
    reject_registration,
    resolve_transcript_asset,
    get_registration_request
)

from App.controllers.password_reset import (
    get_all_password_reset_requests,
    complete_password_reset,
    reject_password_reset
)
import os
from datetime import datetime


requests_views = Blueprint('requests_views', __name__, template_folder='../templates')

VOLUNTEER_REQUESTS_ENDPOINT = 'requests_views.volunteer_requests'

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
        return redirect(url_for(VOLUNTEER_REQUESTS_ENDPOINT))
    
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
        
    return redirect(url_for(VOLUNTEER_REQUESTS_ENDPOINT))

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
        
    return redirect(url_for(VOLUNTEER_REQUESTS_ENDPOINT))

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
    """Stream or redirect to a transcript file for a registration request."""

    registration = get_registration_request(registration_id)
    if not registration:
        flash("Transcript not found", "error")
        return redirect(url_for('requests_views.registrations'))

    asset = resolve_transcript_asset(registration, base_path=current_app.root_path)
    if not asset:
        flash("Transcript not found", "error")
        return redirect(url_for('requests_views.registrations'))

    if asset['mode'] == 'remote':
        return redirect(asset['url'])

    mimetype, _ = mimetypes.guess_type(asset['filename'])
    response = send_file(
        asset['absolute_path'],
        mimetype=mimetype or 'application/pdf',
        as_attachment=False,
        conditional=True
    )
    response.headers['Content-Disposition'] = f'inline; filename="{asset["filename"]}"'
    return response

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


#Password Reset

@requests_views.route('/password-resets')
@jwt_required()
@admin_required
def password_resets():
    """Admin view for managing password reset requests"""
    # Get all password reset requests
    reset_data = get_all_password_reset_requests()
    
    return render_template('admin/requests/password_resets.html', 
                           pending_requests=reset_data['pending'],
                           completed_requests=reset_data['completed'])

@requests_views.route('/api/password-resets/<int:reset_id>/complete', methods=['POST'])
@jwt_required()
@admin_required
def complete_password_reset_endpoint(reset_id):
    """API endpoint to complete a password reset"""
    data = request.json
    new_password = data.get('new_password')
    
    if not new_password:
        return jsonify({
            "success": False,
            "message": "New password is required"
        })
    
    success, message = complete_password_reset(reset_id, new_password, current_user.username)
    
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
        
    return jsonify({
        "success": success,
        "message": message
    })

@requests_views.route('/api/password-resets/<int:reset_id>/reject', methods=['POST'])
@jwt_required()
@admin_required
def reject_password_reset_endpoint(reset_id):
    """API endpoint to reject a password reset"""
    data = request.json
    reason = data.get('reason')
    
    success, message = reject_password_reset(reset_id, current_user.username, reason)
    
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
        
    return jsonify({
        "success": success,
        "message": message
    })