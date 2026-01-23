from flask import request
from flask_jwt_extended import jwt_required
from App.views.api_v2 import api_v2
from App.views.api_v2.utils import api_success, api_error, jwt_required_secure
from App.controllers.assistant_admin import delete_assistant_fully
from App.middleware import admin_required
from App.models import HelpDeskAssistant, LabAssistant, Availability
from App.database import db


@api_v2.route("/assistants", methods=["GET"])
@jwt_required_secure()
@admin_required
def api_get_assistants():
    """Get all assistants (help desk and lab assistants).

    Responses:
      200: success with list of assistants
      500: server error
    """
    try:
        # Get all help desk assistants
        help_desk_assistants = HelpDeskAssistant.query.all()
        lab_assistants = LabAssistant.query.all()

        assistants_data = []

        # Add help desk assistants
        for assistant in help_desk_assistants:
            assistants_data.append(
                {
                    "id": assistant.username,  # username is the primary key
                    "username": assistant.username,
                    "type": "help_desk",
                    "email": getattr(assistant.student, "email", ""),
                    "first_name": getattr(assistant.student, "first_name", ""),
                    "last_name": getattr(assistant.student, "last_name", ""),
                    "rate": float(assistant.rate)
                    if assistant.rate is not None
                    else 20.00,
                    "hours_worked": int(assistant.hours_worked)
                    if assistant.hours_worked is not None
                    else 0,
                    "hours_minimum": int(assistant.hours_minimum)
                    if assistant.hours_minimum is not None
                    else 0,
                    "active": bool(assistant.active),
                    "courses": [
                        cap.course_code
                        for cap in getattr(assistant, "course_capabilities", [])
                    ],
                    "availability": [
                        {
                            "day": avail.day_of_week,
                            "start_time": avail.start_time.strftime("%H:%M"),
                            "end_time": avail.end_time.strftime("%H:%M"),
                        }
                        for avail in Availability.query.filter_by(
                            username=assistant.username
                        ).all()
                    ],
                }
            )

        # Add lab assistants
        for assistant in lab_assistants:
            assistants_data.append(
                {
                    "id": assistant.username,  # username is the primary key
                    "username": assistant.username,
                    "type": "lab",
                    "email": getattr(assistant.student, "email", ""),
                    "first_name": getattr(assistant.student, "first_name", ""),
                    "last_name": getattr(assistant.student, "last_name", ""),
                    "active": bool(assistant.active),
                    "experience": bool(assistant.experience),
                    "courses": [],  # Lab assistants don't have course capabilities by default
                    "availability": [
                        {
                            "day": avail.day_of_week,
                            "start_time": avail.start_time.strftime("%H:%M")
                            if avail.start_time
                            else None,
                            "end_time": avail.end_time.strftime("%H:%M")
                            if avail.end_time
                            else None,
                        }
                        for avail in Availability.query.filter_by(
                            username=assistant.username
                        ).all()
                    ],
                }
            )

        return api_success(
            data=assistants_data, message="Assistants retrieved successfully"
        )

    except Exception as e:
        return api_error(f"Failed to retrieve assistants: {str(e)}", status_code=500)


@api_v2.route("/admin/assistants/<username>", methods=["DELETE"])
@jwt_required_secure()
@admin_required
def api_delete_assistant(username):
    """Delete an assistant and cascade related data.

    Responses:
      200: success
      400/404/409: domain errors
      500: server
    """
    success, payload = delete_assistant_fully(username)
    if success:
        return api_success(payload, message=payload.get("message", "Assistant deleted"))
    code = payload.get("code", 400)
    return api_error(payload.get("message", "Deletion failed"), status_code=code)
