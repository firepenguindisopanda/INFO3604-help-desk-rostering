from flask_jwt_extended import create_access_token, jwt_required, JWTManager, get_jwt_identity, verify_jwt_in_request
from App.models import User

def login(username, password):
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        access_token = create_access_token(
            identity=str(username),
            additional_claims={'role': user.role}  
        )
        return access_token, user.role
    return None, None

def setup_jwt(app):
    jwt = JWTManager(app)

    @jwt.user_identity_loader
    def user_identity_lookup(identity):
        return str(identity)

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return User.query.filter_by(username=identity).first()

    return jwt

def add_auth_context(app):
    @app.context_processor
    def inject_user():
        try:
            verify_jwt_in_request()
            identity = get_jwt_identity()
            current_user = User.query.filter_by(username=identity).first()
            is_authenticated = True if current_user else False
        except Exception as e:
            print(f"Auth context error: {e}")
            is_authenticated = False
            current_user = None
        return dict(is_authenticated=is_authenticated, current_user=current_user)