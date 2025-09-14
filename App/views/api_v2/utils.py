from flask import jsonify

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
        "data": data or {}
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