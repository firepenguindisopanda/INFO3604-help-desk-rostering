from flask import jsonify, request, current_app
from flask_jwt_extended import jwt_required, verify_jwt_in_request
try:
    import flask_jwt_extended.exceptions as _jwt_exceptions  # type: ignore
except ImportError:  # pragma: no cover - fallback for older flask-jwt-extended versions
    _jwt_exceptions = None

CSRFError = getattr(_jwt_exceptions, "CSRFError", Exception)
from functools import wraps
import os


def _preview_token(token_value):
    """Return a shortened preview of a token for logging without leaking secrets."""
    if not token_value:
        return None
    cleaned = str(token_value)
    if len(cleaned) <= 8:
        return cleaned
    return f"{cleaned[:4]}...{cleaned[-4:]}"


def _log_jwt_request_context():
    """Emit debug information about the incoming JWT-related request context."""
    auth_header = request.headers.get('Authorization')
    csrf_header = request.headers.get('X-CSRF-TOKEN')
    access_cookie_name = current_app.config.get('JWT_ACCESS_COOKIE_NAME', 'access_token')
    access_cookie = request.cookies.get(access_cookie_name)
    csrf_cookie = request.cookies.get('csrf_access_token')

    current_app.logger.debug(
        "API v2 JWT guard: path=%s method=%s auth_header=%s csrf_header_present=%s "
        "access_cookie=%s csrf_cookie=%s is_secure=%s forwarded_proto=%s",
        request.path,
        request.method,
        _preview_token(auth_header),
        bool(csrf_header),
        _preview_token(access_cookie),
        bool(csrf_cookie),
        request.is_secure,
        request.headers.get('X-Forwarded-Proto')
    )


def api_success(data=None, message=None, status_code=200):
    """
    Standardized success response format for API v2
    
    Args:
        data: The data to return (dict, list, or None)
        message: Optional success message
        status_code: HTTP status code (default: 200)
        
    Returns:
        Flask response with JSON and status code
    """
    response = {
        "success": True,
        "data": data if data is not None else {}
    }
    if message:
        response["message"] = message
    return jsonify(response), status_code

def api_error(message="An error occurred", errors=None, status_code=400):
    """
    Standardized error response format for API v2
    
    Args:
        message: Error message to display
        errors: Optional dict/list of detailed errors
        status_code: HTTP status code (default: 400)
        
    Returns:
        Flask response with JSON and status code
    """
    response = {
        "success": False,
        "message": message
    }
    if errors:
        response["errors"] = errors
    return jsonify(response), status_code

def validate_json_request(request):
    """
    Validate that a request contains JSON data
    
    Args:
        request: Flask request object
        
    Returns:
        tuple: (data, error_response) - data will be None if error
    """
    if not request.is_json:
        return None, api_error("Request must include JSON body with Content-Type: application/json", status_code=400)
    
    data = request.get_json()
    if not data:
        return None, api_error("Request body must contain valid JSON", status_code=400)
    
    return data, None

def _verify_jwt_prefer_header():
    """Verify JWT, preferring Authorization header when supplied."""
    auth_header = request.headers.get('Authorization', '') or ''

    # If no Authorization header and no cookie parsed into request.cookies, attempt to
    # recover an access token from a raw 'Cookie' header (some tests/clients set Cookie in
    # headers rather than the WSGI environ). If found, inject it into the request environ
    # as HTTP_AUTHORIZATION so flask-jwt-extended can pick it up via headers.
    if not auth_header:
        access_cookie_name = current_app.config.get('JWT_ACCESS_COOKIE_NAME', 'access_token')
        # If request.cookies doesn't contain the access cookie but a raw Cookie header exists,
        # try to parse it.
        if not request.cookies.get(access_cookie_name):
            cookie_header = request.headers.get('Cookie') or request.environ.get('HTTP_COOKIE')
            if cookie_header:
                try:
                    from http.cookies import SimpleCookie
                    sc = SimpleCookie()
                    sc.load(cookie_header)
                    if access_cookie_name in sc:
                        token_value = sc[access_cookie_name].value
                        # Inject Authorization into environ so verify_jwt_in_request can find it
                        request.environ['HTTP_AUTHORIZATION'] = f'Bearer {token_value}'
                        auth_header = request.environ.get('HTTP_AUTHORIZATION')
                        current_app.logger.debug("API v2 JWT guard: extracted token from Cookie header into Authorization env")
                except Exception:
                    current_app.logger.exception("Failed to parse Cookie header for access token")

    if auth_header.lower().startswith('bearer '):
        current_app.logger.debug("API v2 JWT guard: verifying via Authorization header")
        verify_jwt_in_request(locations=["headers"])
    else:
        current_app.logger.debug("API v2 JWT guard: verifying via default locations (headers/cookies)")
        verify_jwt_in_request()


def _enforce_production_security():
    """Apply additional production-only checks for secure API usage."""
    if not current_app.config.get("JWT_COOKIE_SECURE", False):
        return None

    forwarded_proto = (request.headers.get('X-Forwarded-Proto') or '').lower()
    if not request.is_secure and forwarded_proto != 'https':
        return api_error(
            "Secure connection required for API v2 in production",
            status_code=400
        )

    if current_app.config.get("JWT_COOKIE_CSRF_PROTECT", False):
        # JWT-Extended handles CSRF validation automatically when enabled
        pass

    current_app.logger.info(
        f"API v2 secure request: {request.method} {request.path} "
        f"from {request.remote_addr} (HTTPS: {request.is_secure})"
    )
    return None


def jwt_required_secure():
    """
    Enhanced JWT required decorator for API v2 routes that enforces secure cookies in production
    
    This decorator:
    1. Verifies JWT token as normal
    2. Enforces secure cookie requirements for API v2 routes in production
    3. Validates CSRF tokens when secure cookies are enabled
    
    Returns:
        Decorator function that can be applied to API v2 routes
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Check if we're in production environment
                is_production = os.environ.get('ENV', 'development') == 'production'
                _log_jwt_request_context()

                _verify_jwt_prefer_header()
                
                # Additional security checks for API v2 in production
                if is_production:
                    enforcement_error = _enforce_production_security()
                    if enforcement_error:
                        return enforcement_error
                
                return f(*args, **kwargs)
                
            except CSRFError as csrf_error:
                current_app.logger.warning(f"API v2 JWT security check failed: {str(csrf_error)}")
                return api_error(
                    "Authentication requires CSRF token",
                    errors={
                        "auth": "Missing CSRF token. Include X-CSRF-TOKEN when using cookie authentication or send the JWT in the Authorization header."
                    },
                    status_code=401
                )
            except Exception as e:
                current_app.logger.warning(f"API v2 JWT security check failed: {str(e)}")
                return api_error(
                    "Authentication required",
                    errors={"auth": "Invalid or missing authentication token"},
                    status_code=401
                )
        
        return decorated_function
    return decorator

def validate_json_request_secure(required_fields=None):
    """
    Enhanced JSON validation for API v2 with security checks
    
    Args:
        required_fields: List of required field names
        
    Returns:
        tuple: (data, error_response) - data will be None if error
    """
    if not request.is_json:
        return None, api_error(
            "Request must include JSON body with Content-Type: application/json", 
            status_code=400
        )
    
    data = request.get_json()
    if not data:
        return None, api_error("Request body must contain valid JSON", status_code=400)
    
    # Validate required fields if specified
    if required_fields:
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            return None, api_error(
                "Missing required fields",
                errors=dict.fromkeys(missing_fields, "Required"),
                status_code=400
            )
    
    # Security: Log potentially sensitive operations in production
    is_production = os.environ.get('ENV', 'development') == 'production'
    if is_production:
        # Log request details for security monitoring (but not the actual data)
        current_app.logger.info(
            f"API v2 JSON request: {request.method} {request.path} "
            f"fields: {list(data.keys()) if data else []}"
        )
    
    return data, None