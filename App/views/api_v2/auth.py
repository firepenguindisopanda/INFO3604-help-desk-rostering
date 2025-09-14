from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from App.views.api_v2 import api_v2
from App.views.api_v2.utils import api_success, api_error, validate_json_request
from App.controllers.auth import login as auth_login
from App.controllers.user import get_user

@api_v2.route('/auth/login', methods=['POST'])
def login():
    """
    Authenticate user and return JWT token
    
    Expected JSON body:
    {
        "username": "string",
        "password": "string"
    }
    
    Returns:
        Success: JWT token and user info
        Error: Authentication failure message
    """
    data, error = validate_json_request(request)
    if error:
        return error
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return api_error("Username and password are required", status_code=400)
    
    # Call existing login controller
    token, user_type = auth_login(username, password)

    if not token:
        return api_error("Invalid username or password", status_code=401)

    # Fetch the user entity for response details
    user_entity = get_user(username)
    if not user_entity:
        # Should not happen if auth_login succeeded, but guard anyway
        return api_error("User record not found after authentication", status_code=500)

    # Determine user role and type
    is_admin = hasattr(user_entity, 'role') or user_type == 'admin'
    role = getattr(user_entity, 'role', None)

    return api_success({
        "user": {
            "username": user_entity.username,
            "email": getattr(user_entity, 'email', ''),
            "first_name": getattr(user_entity, 'first_name', ''),
            "last_name": getattr(user_entity, 'last_name', ''),
            "role": role,
            "is_admin": is_admin,
        },
        "token": token
    }, "Login successful")

@api_v2.route('/auth/register', methods=['POST'])
def register():
    """
    Register a new user (student) account
    
    Supports two content types:
    - multipart/form-data (preferred; supports file uploads: profile_picture, transcript)
    - application/json (no files; will return error because profile picture upload is required)
    
    Expected form fields (multipart/form-data):
    - student_id (alias: username) [required]
    - name OR (first_name and last_name) [required]
    - email [required]
    - phone [required]
    - degree [required, e.g. BSc|MSc]
    - password [required] and confirm_password [required]
    - reason [required]
    - terms [required; "on"/"true" to confirm]
    - courses[] (repeat field) or courses (JSON array) [required]
    - availability (JSON array of slots) or availability_slots (JSON) [required]
    - files: profile_picture (required), transcript (optional)
    
    JSON requests are supported only for structure validation and will error if profile_picture is not provided as multipart.
    
    Returns:
        Success: Registration confirmation
        Error: Registration failure message
    """
    # Helpers for validation
    def _bool_true(val):
        if val is None:
            return False
        if isinstance(val, bool):
            return val
        return str(val).strip().lower() in {"true", "1", "on", "yes"}

    # Handle multipart form-data (supports file uploads)
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        form = request.form
        username = form.get('username') or form.get('student_id')
        password = form.get('password')
        confirm_password = form.get('confirm_password')
        name = form.get('name')
        first_name = form.get('first_name')
        last_name = form.get('last_name')
        email = form.get('email')
        degree = form.get('degree')
        phone = form.get('phone')
        reason = form.get('reason')
        terms = form.get('terms') or form.get('confirm')

        # files: support multiple common field names
        profile_picture_file = (
            request.files.get('profile_picture')
            or request.files.get('profile_picture_file')
            or request.files.get('profilePicture')
        )
        transcript_file = request.files.get('transcript') or request.files.get('transcript_file')

        # courses: support repeated fields and JSON
        courses = form.getlist('courses[]')
        if not courses:
            courses_raw = form.get('courses')
            if courses_raw:
                try:
                    import json
                    parsed = json.loads(courses_raw)
                    if isinstance(parsed, list):
                        courses = parsed
                    elif isinstance(parsed, str):
                        courses = [parsed]
                except Exception:
                    # comma-separated fallback
                    courses = [c.strip() for c in courses_raw.split(',') if c.strip()]
            else:
                # also support repeated 'courses' without [] suffix
                courses = form.getlist('courses')

        # availability: prefer 'availability' JSON, fallback to 'availability_slots'
        availability_raw = form.get('availability') or form.get('availability_slots')
        availability_slots = None
        if availability_raw:
            try:
                import json
                parsed = json.loads(availability_raw)
                if isinstance(parsed, list):
                    availability_slots = parsed
            except Exception:
                availability_slots = None
    else:
        # Default to JSON handling
        data, error = validate_json_request(request)
        if error:
            return error
        username = data.get('username') or data.get('student_id')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        name = data.get('name')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        degree = data.get('degree')
        phone = data.get('phone')
        reason = data.get('reason')
        terms = data.get('terms') or data.get('confirm')
        courses = data.get('courses') or data.get('course_codes')
        availability_slots = data.get('availability') or data.get('availability_slots')
        profile_picture_file = None
        transcript_file = None

    # Normalize name from first/last if needed
    if not name:
        name_parts = [p for p in [first_name, last_name] if p]
        name = " ".join(name_parts).strip() if name_parts else None

    # Validate required fields (frontend requires these)
    missing = []
    if not username:
        missing.append('student_id')
    if not name:
        missing.append('name')
    if not email:
        missing.append('email')
    if not phone:
        missing.append('phone')
    if not degree:
        missing.append('degree')
    if not password:
        missing.append('password')
    if confirm_password is None:
        missing.append('confirm_password')
    elif password != confirm_password:
        return api_error('Passwords do not match', status_code=400)
    if not reason:
        missing.append('reason')
    if not _bool_true(terms):
        missing.append('terms')
    if not courses or (isinstance(courses, list) and len(courses) == 0):
        missing.append('courses')
    if not availability_slots or (isinstance(availability_slots, list) and len(availability_slots) == 0):
        missing.append('availability')
    # Files required: profile picture and transcript must be present (JSON requests will fail here)
    if profile_picture_file is None:
        return api_error('Profile picture is required and must be uploaded as multipart/form-data', status_code=400)
    if transcript_file is None:
        return api_error('Transcript (PDF) is required and must be uploaded as multipart/form-data', status_code=400)
    if missing:
        return api_error(f"Missing required fields: {', '.join(missing)}", status_code=400)

    # Basic password policy (mirror legacy UI)
    pw = password or ''
    if len(pw) < 8 or not any(c.isupper() for c in pw) or not any(c.isdigit() for c in pw) or not any(not c.isalnum() for c in pw):
        return api_error('Password must be at least 8 characters, include an uppercase letter, a number, and a special character', status_code=400)

    try:
        # Import here to avoid circular imports
        from App.controllers.registration import create_registration_request

        # Call controller with correct signature
        success, message = create_registration_request(
            username=username,
            name=name,
            email=email,
            degree=degree,
            reason=reason,
            phone=phone,
            transcript_file=transcript_file,
            profile_picture_file=profile_picture_file,
            courses=courses,
            password=password,
            availability_slots=availability_slots,
        )

        if not success:
            # Map common failure cases to appropriate status codes
            code = 409 if 'already' in (message or '').lower() or 'exists' in (message or '').lower() else 400
            return api_error(message or "Registration failed", status_code=code)

        return api_success(
            {"username": username},
            message or "Registration request submitted successfully. Your account will be activated once approved by an administrator."
        )
    except Exception as e:
        return api_error(f"Registration failed: {str(e)}", status_code=500)

@api_v2.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout current user (client should remove token)
    
    Returns:
        Success message
    """
    # With JWT, logout is typically handled client-side by removing the token
    # We could implement token blacklisting here if needed
    return api_success(message="Logged out successfully")

@api_v2.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get current authenticated user's profile information
    
    Returns:
        Current user's profile data
    """
    username = get_jwt_identity()
    user = get_user(username)
    
    if not user:
        return api_error("User not found", status_code=404)
    
    is_admin = hasattr(user, 'role')
    role = getattr(user, 'role', None)
    
    return api_success({
        "username": user.username,
        "email": getattr(user, 'email', ''),
        "first_name": getattr(user, 'first_name', ''),
        "last_name": getattr(user, 'last_name', ''),
        "is_admin": is_admin,
        "role": role,
        "student_id": getattr(user, 'student_id', None) if not is_admin else None,
        "created_at": getattr(user, 'created_at', None).isoformat() if hasattr(user, 'created_at') and getattr(user, 'created_at') else None,
    })

@api_v2.route('/me', methods=['PUT'])
@jwt_required()
def update_current_user():
    """
    Update current authenticated user's profile information
    
    Expected JSON body:
    {
        "email": "string" (optional),
        "first_name": "string" (optional),
        "last_name": "string" (optional)
    }
    
    Returns:
        Updated user profile data
    """
    data, error = validate_json_request(request)
    if error:
        return error
    
    username = get_jwt_identity()
    user = get_user(username)
    
    if not user:
        return api_error("User not found", status_code=404)
    
    try:
        # Update allowed fields
        if 'email' in data:
            user.email = data['email']
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        
        # Save changes
        from App.database import db
        db.session.commit()
        
        # Return updated user data
        is_admin = hasattr(user, 'role')
        role = getattr(user, 'role', None)
        
        return api_success({
            "username": user.username,
            "email": getattr(user, 'email', ''),
            "first_name": getattr(user, 'first_name', ''),
            "last_name": getattr(user, 'last_name', ''),
            "is_admin": is_admin,
            "role": role,
            "student_id": getattr(user, 'student_id', None) if not is_admin else None,
        }, "Profile updated successfully")
        
    except Exception as e:
        from App.database import db
        db.session.rollback()
        return api_error(f"Failed to update profile: {str(e)}", status_code=500)