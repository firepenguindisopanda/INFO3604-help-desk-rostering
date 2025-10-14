from flask import request
from flask_jwt_extended import jwt_required
from App.views.api_v2 import api_v2
from App.views.api_v2.utils import api_success, api_error, jwt_required_secure
from App.controllers.assistant_admin import delete_assistant_fully
from App.middleware import admin_required
from App.models import HelpDeskAssistant, LabAssistant
from App.database import db


@api_v2.route('/assistants', methods=['GET'])
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
            assistants_data.append({
                'id': assistant.id,
                'username': assistant.user.username,
                'type': 'help_desk',
                'email': getattr(assistant.user, 'email', ''),
                'first_name': getattr(assistant.user, 'first_name', ''),
                'last_name': getattr(assistant.user, 'last_name', '')
            })
        
        # Add lab assistants
        for assistant in lab_assistants:
            assistants_data.append({
                'id': assistant.id,
                'username': assistant.user.username,
                'type': 'lab',
                'email': getattr(assistant.user, 'email', ''),
                'first_name': getattr(assistant.user, 'first_name', ''),
                'last_name': getattr(assistant.user, 'last_name', '')
            })
        
        return api_success(data=assistants_data, message="Assistants retrieved successfully")
        
    except Exception as e:
        return api_error(f"Failed to retrieve assistants: {str(e)}", status_code=500)


@api_v2.route('/admin/assistants/<username>', methods=['DELETE'])
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
