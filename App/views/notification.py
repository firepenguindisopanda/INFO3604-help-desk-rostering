from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from flask_jwt_extended import jwt_required, current_user
from App.controllers import (
    get_user_notifications,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    delete_notification,
    count_unread_notifications
)
from App.middleware import admin_required, volunteer_required

notification_views = Blueprint('notification_views', __name__, template_folder='../templates')

# API endpoints for notifications
@notification_views.route('/api/notifications', methods=['GET'])
@jwt_required()
def get_notifications_api():
    """Get notifications for the current user"""
    limit = request.args.get('limit', 10, type=int)
    include_read = request.args.get('include_read', False, type=bool)
    
    notifications = get_user_notifications(current_user.username, limit, include_read)
    return jsonify([notification.get_json() for notification in notifications])

@notification_views.route('/api/notifications/count', methods=['GET'])
@jwt_required()
def count_notifications_api():
    """Count unread notifications for the current user"""
    count = count_unread_notifications(current_user.username)
    return jsonify({'count': count})

@notification_views.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@jwt_required()
def mark_as_read_api(notification_id):
    """Mark a notification as read"""
    success = mark_notification_as_read(notification_id)
    return jsonify({'success': success})

@notification_views.route('/api/notifications/read-all', methods=['POST'])
@jwt_required()
def mark_all_as_read_api():
    """Mark all notifications as read"""
    count = mark_all_notifications_as_read(current_user.username)
    return jsonify({'success': True, 'count': count})

@notification_views.route('/api/notifications/<int:notification_id>', methods=['DELETE'])
@jwt_required()
def delete_notification_api(notification_id):
    """Delete a notification"""
    success = delete_notification(notification_id)
    return jsonify({'success': success})

# Admin notification page
@notification_views.route('/admin/notifications')
@jwt_required()
@admin_required
def admin_notifications():
    """Notification page for admin users"""
    return render_template('admin/notifications/index.html')

# Volunteer notification page
@notification_views.route('/volunteer/notifications')
@jwt_required()
@volunteer_required
def volunteer_notifications():
    """Notification page for volunteer users"""
    return render_template('volunteer/notifications/index.html')