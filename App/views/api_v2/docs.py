import copy
import re
from typing import Dict, List, Optional, Tuple

from flask import current_app, jsonify, render_template_string, url_for

from App.views.api_v2 import api_v2

# Basic Swagger UI page served via CDN to avoid new dependencies.
SWAGGER_UI_TEMPLATE = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>API v2 Docs</title>
  <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css\" />
  <style>
    body { margin: 0; padding: 0; }
    #swagger-ui { margin: 0; }
  </style>
</head>
<body>
  <div id=\"swagger-ui\"></div>
  <script src=\"https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js\"></script>
  <script>
    window.onload = () => {
      SwaggerUIBundle({
        url: "{{ spec_url }}",
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [SwaggerUIBundle.presets.apis],
        layout: 'BaseLayout'
      });
    };
  </script>
</body>
</html>"""

_ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}
JSON_CT = "application/json"
API_MESSAGE_REF = "#/components/schemas/ApiMessage"


def _rule_to_openapi_path(rule: str) -> str:
    """Convert Flask rule syntax to OpenAPI path syntax."""
    return re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", rule)


def _tag_from_rule(rule: str) -> str:
    """Derive a simple tag from the first path segment after /api/v2."""
    trimmed = rule.replace("/api/v2/", "", 1)
    return trimmed.split("/", 1)[0] or "api"


def _success_response(schema_ref: str, example: Optional[dict] = None) -> dict:
    content = {JSON_CT: {"schema": {"$ref": schema_ref}}}
    if example:
        content[JSON_CT]["example"] = example
    return {"description": "Success", "content": content}


def _error_response() -> dict:
    return {
        "description": "Error",
        "content": {
            JSON_CT: {
                "schema": {"$ref": "#/components/schemas/ApiError"}
            }
        }
    }


def _get_override(path: str, method: str) -> Optional[dict]:
    return _OVERRIDES.get((path, method))


def _merge_dict(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged.get(key, {}), value)
        else:
            merged[key] = value
    return merged


def _build_paths() -> Dict[str, Dict[str, dict]]:
    paths: Dict[str, Dict[str, dict]] = {}
    for rule in current_app.url_map.iter_rules():
        if not rule.rule.startswith("/api/v2"):
            continue
        if rule.endpoint.endswith("static"):
            continue

        methods: List[str] = [m for m in rule.methods if m in _ALLOWED_METHODS]
        if not methods:
            continue

        openapi_path = _rule_to_openapi_path(rule.rule)
        path_item: Dict[str, dict] = {}

        for method in methods:
            operation = {
                "summary": rule.endpoint,
                "responses": {
                    "200": {"description": "Success"},
                    "400": _error_response(),
                    "401": _error_response(),
                },
                "tags": [_tag_from_rule(rule.rule)]
            }

            override = _get_override(openapi_path, method.lower())
            if override:
                operation = _merge_dict(operation, override)

            path_item[method.lower()] = operation

        paths[openapi_path] = path_item

    return paths


COMPONENT_SCHEMAS: Dict[str, dict] = {
    "ApiError": {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "example": False},
            "message": {"type": "string"},
            "errors": {"type": "object"}
        },
        "required": ["success", "message"]
    },
    "ApiMessage": {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "example": True},
            "message": {"type": "string"},
            "data": {"type": "object"}
        },
        "required": ["success"]
    },
    "Notification": {
        "type": "object",
        "properties": {
            "id": {"type": "integer", "example": 123},
            "username": {"type": "string", "example": "a"},
            "message": {"type": "string", "example": "Schedule published"},
            "notification_type": {"type": "string", "example": "schedule"},
            "is_read": {"type": "boolean", "example": False},
            "created_at": {"type": "string", "format": "date-time"},
            "friendly_time": {"type": "string", "example": "Today at 03:00 PM"}
        },
        "required": ["id", "username", "message", "notification_type", "is_read", "created_at"]
    },
    "NotificationListResponse": {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "example": True},
            "data": {
                "type": "object",
                "properties": {
                    "notifications": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Notification"}
                    },
                    "count": {"type": "integer", "example": 2},
                    "unread_count": {"type": "integer", "example": 1}
                }
            }
        }
    },
    "UnreadCountResponse": {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "example": True},
            "data": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "example": 3}
                }
            }
        }
    },
    "PublishResponse": {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "example": True},
            "data": {
                "type": "object",
                "properties": {
                    "schedule_id": {"type": "integer", "example": 1},
                    "published_at": {"type": "string", "format": "date-time"},
                    "notifications_sent": {"type": "integer", "example": 10}
                }
            },
            "message": {"type": "string", "example": "Schedule published successfully"}
        }
    },
    "PublishWithSyncResponse": {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "example": True},
            "data": {
                "type": "object",
                "properties": {
                    "schedule_id": {"type": "integer", "example": 1},
                    "published_at": {"type": "string", "format": "date-time"},
                    "sync_status": {"type": "string", "example": "success"},
                    "message": {"type": "string", "example": "Schedule published and synced"}
                }
            },
            "message": {"type": "string", "example": "Schedule published with sync"}
        }
    },
    "StaffProfile": {
        "type": "object",
        "properties": {
            "username": {"type": "string", "example": "student1"},
            "name": {"type": "string", "example": "Jane Doe"},
            "degree": {"type": "string", "example": "BSc"},
            "active": {"type": "boolean", "example": True},
            "rate": {"type": "number", "format": "float", "example": 25.0},
            "hours_worked": {"type": "number", "example": 12},
            "hours_minimum": {"type": "number", "example": 6},
            "courses": {"type": "array", "items": {"type": "string"}},
            "availabilities": {"type": "array", "items": {"type": "object"}},
            "email": {"type": "string", "example": "student1@my.uwi.edu"},
            "phone": {"type": "string", "example": "868-555-1234"},
            "profile_image_url": {"type": "string", "example": "/static/uploads/profile.png"}
        }
    },
    "StaffProfileUpdateRequest": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "degree": {"type": "string"},
            "rate": {"type": "number"},
            "hours_minimum": {"type": "integer"},
            "active": {"type": "boolean"},
            "email": {"type": "string"},
            "phone": {"type": "string"},
            "courses": {"type": "array", "items": {"type": "string"}},
            "availabilities": {"type": "array", "items": {"type": "object"}}
        }
    },
    "StudentProfileUpdateRequest": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "degree": {"type": "string"},
            "rate": {"type": "number"},
            "hours_minimum": {"type": "integer"},
            "active": {"type": "boolean"}
        }
    },
    "StaffProfileResponse": {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "example": True},
            "data": {
                "type": "object",
                "properties": {
                    "profile": {"$ref": "#/components/schemas/StaffProfile"}
                }
            }
        }
    },
    "AdminProfileResponse": {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "example": True},
            "data": {
                "type": "object",
                "properties": {
                    "profile": {"type": "object"},
                    "students": {"type": "array", "items": {"type": "object"}}
                }
            }
        }
    }
}


_OVERRIDES: Dict[Tuple[str, str], dict] = {
    ("/api/v2/notifications", "get"): {
        "summary": "List notifications for current user",
        "responses": {
            "200": _success_response("#/components/schemas/NotificationListResponse")
        },
        "parameters": [
            {
                "name": "limit",
                "in": "query",
                "schema": {"type": "integer", "default": 20},
                "description": "Maximum notifications to return"
            },
            {
                "name": "include_read",
                "in": "query",
                "schema": {"type": "boolean", "default": False},
                "description": "Include read notifications"
            }
        ]
    },
    ("/api/v2/notifications/count", "get"): {
        "summary": "Unread notifications count",
        "responses": {
            "200": _success_response("#/components/schemas/UnreadCountResponse")
        }
    },
    ("/api/v2/notifications/{notification_id}/read", "post"): {
        "summary": "Mark notification as read",
        "responses": {
            "200": _success_response(API_MESSAGE_REF, example={"success": True, "data": {"unread_count": 2}, "message": "Notification marked as read"})
        }
    },
    ("/api/v2/notifications/read-all", "post"): {
        "summary": "Mark all notifications as read",
        "responses": {
            "200": _success_response(API_MESSAGE_REF, example={"success": True, "data": {"updated": 5, "unread_count": 0}, "message": "All notifications marked as read"})
        }
    },
    ("/api/v2/notifications/{notification_id}", "delete"): {
        "summary": "Delete notification",
        "responses": {
            "200": _success_response(API_MESSAGE_REF, example={"success": True, "data": {"deleted": 1, "unread_count": 1}, "message": "Notification deleted"})
        }
    },
    ("/api/v2/admin/schedule/{schedule_id}/publish", "post"): {
        "summary": "Publish schedule",
        "responses": {
            "200": _success_response("#/components/schemas/PublishResponse")
        }
    },
    ("/api/v2/admin/schedule/{schedule_id}/publish-with-sync", "post"): {
        "summary": "Publish schedule with sync",
        "responses": {
            "200": _success_response("#/components/schemas/PublishWithSyncResponse")
        }
    },
    ("/api/v2/profiles/staff/{username}", "get"): {
        "summary": "Get staff profile",
        "responses": {
            "200": _success_response("#/components/schemas/StaffProfileResponse")
        }
    },
    ("/api/v2/profiles/staff/{username}", "put"): {
        "summary": "Admin update staff profile",
        "requestBody": {
            "required": True,
            "content": {
                JSON_CT: {
                    "schema": {"$ref": "#/components/schemas/StaffProfileUpdateRequest"}
                }
            }
        },
        "responses": {
            "200": _success_response(API_MESSAGE_REF, example={"success": True, "message": "Profile updated successfully", "data": {"username": "student1"}})
        }
    },
    ("/api/v2/profiles/students/{username}", "put"): {
        "summary": "Admin update student profile",
        "requestBody": {
            "required": True,
            "content": {
                JSON_CT: {
                    "schema": {"$ref": "#/components/schemas/StudentProfileUpdateRequest"}
                }
            }
        },
        "responses": {
            "200": _success_response(API_MESSAGE_REF, example={"success": True, "message": "Student profile updated successfully", "data": {"username": "student1"}})
        }
    },
    ("/api/v2/profiles/admin", "get"): {
        "summary": "Admin profile context",
        "responses": {
            "200": _success_response("#/components/schemas/AdminProfileResponse")
        }
    }
}


def _build_spec() -> Dict:
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Help Desk Rostering API v2",
            "version": current_app.config.get("VERSION", "0.0.0"),
            "description": "Auto-generated list of /api/v2 routes with examples"
        },
        "servers": [
            {"url": ""}
        ],
        "paths": _build_paths(),
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            },
            "schemas": COMPONENT_SCHEMAS,
        },
        "security": [{"bearerAuth": []}]
    }


@api_v2.route('/openapi.json', methods=['GET'])
def openapi_json():
    """Return an OpenAPI spec generated from registered /api/v2 routes."""
    return jsonify(_build_spec())


@api_v2.route('/docs', methods=['GET'])
def swagger_ui():
    """Serve an in-browser Swagger UI for the generated spec."""
    spec_url = url_for('api_v2.openapi_json', _external=False)
    html = render_template_string(SWAGGER_UI_TEMPLATE, spec_url=spec_url)
    return html
