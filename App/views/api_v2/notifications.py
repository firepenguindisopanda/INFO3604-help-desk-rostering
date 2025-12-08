from flask import request
from flask_jwt_extended import get_jwt_identity

from App.controllers.notification import (
    count_unread_notifications,
    delete_notification,
    get_notification,
    get_user_notifications,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)
from App.views.api_v2 import api_v2
from App.views.api_v2.utils import api_error, api_success, jwt_required_secure


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "on")
    return bool(value)


def _ensure_owner(notification_id: int, username: str):
    notification = get_notification(notification_id)
    if not notification:
        return None, api_error("Notification not found", status_code=404)
    if notification.username != username:
        return None, api_error("Forbidden: cannot modify another user's notification", status_code=403)
    return notification, None


@api_v2.route('/notifications', methods=['GET'])
@jwt_required_secure()
def list_notifications():
    """List notifications for the authenticated user."""
    username = get_jwt_identity()
    limit = request.args.get('limit', 20, type=int)
    include_read = _parse_bool(request.args.get('include_read'), default=False)

    notifications = get_user_notifications(username, limit=limit, include_read=include_read)
    unread_count = count_unread_notifications(username)

    return api_success(
        data={
            "notifications": [n.get_json() for n in notifications],
            "count": len(notifications),
            "unread_count": unread_count,
        }
    )


@api_v2.route('/notifications/count', methods=['GET'])
@jwt_required_secure()
def count_notifications():
    """Return unread notification count for the authenticated user."""
    username = get_jwt_identity()
    count = count_unread_notifications(username)
    return api_success({"count": count})


@api_v2.route('/notifications/<int:notification_id>/read', methods=['POST'])
@jwt_required_secure()
def mark_notification_read(notification_id: int):
    """Mark a notification as read (owner only)."""
    username = get_jwt_identity()
    notification, error = _ensure_owner(notification_id, username)
    if error:
        return error

    mark_notification_as_read(notification.id)
    unread_count = count_unread_notifications(username)
    return api_success({"unread_count": unread_count}, message="Notification marked as read")


@api_v2.route('/notifications/read-all', methods=['POST'])
@jwt_required_secure()
def mark_all_notifications_read():
    """Mark all notifications as read for the authenticated user."""
    username = get_jwt_identity()
    count = mark_all_notifications_as_read(username)
    return api_success({"updated": count, "unread_count": 0}, message="All notifications marked as read")


@api_v2.route('/notifications/<int:notification_id>', methods=['DELETE'])
@jwt_required_secure()
def delete_notification_route(notification_id: int):
    """Delete a notification (owner only)."""
    username = get_jwt_identity()
    notification, error = _ensure_owner(notification_id, username)
    if error:
        return error

    delete_notification(notification.id)
    unread_count = count_unread_notifications(username)
    return api_success({"deleted": notification.id, "unread_count": unread_count}, message="Notification deleted")
