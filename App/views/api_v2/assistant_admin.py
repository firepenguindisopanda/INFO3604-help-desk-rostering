from flask import request
from flask_jwt_extended import jwt_required
from App.views.api_v2 import api_v2
from App.views.api_v2.utils import api_success, api_error, jwt_required_secure
from App.controllers.assistant_admin import delete_assistant_fully
from App.middleware import admin_required


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
