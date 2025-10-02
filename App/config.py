import os
from datetime import timedelta

def load_config(app, overrides):
    if os.path.exists(os.path.join('./App', 'custom_config.py')):
        app.config.from_object('App.custom_config')
    else:
        app.config.from_object('App.default_config')
    
    app.config.from_prefixed_env()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    app.config['UPLOADED_PHOTOS_DEST'] = "App/uploads"
    
    db_url = (
        os.environ.get('DATABASE_URI_NEON') or
        os.environ.get('DATABASE_URI_SQLITE') or
        os.environ.get('DATABASE_URI_POSTGRES_LOCAL') or
        app.config.get('SQLALCHEMY_DATABASE_URI')
    )
    if db_url:
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
        print(f"Using database URI: {db_url}")
    else:
        print("Warning: No database URI configured")

    # Ensure SQLAlchemy re-establishes dropped connections (e.g., idle Postgres SSL timeouts)
    engine_options = app.config.setdefault('SQLALCHEMY_ENGINE_OPTIONS', {})
    engine_options.setdefault('pool_pre_ping', True)
    engine_options.setdefault('pool_recycle', 280)
    engine_options.setdefault('pool_timeout', 30)
    
    # JWT Configuration
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
    app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token'
    app.config["JWT_TOKEN_LOCATION"] = ["cookies", "headers"]
    
    # Secure JWT settings for production (API v2 routes will enforce these)
    is_production = os.environ.get('ENV', 'development') == 'production'
    app.config["JWT_COOKIE_SECURE"] = is_production  # True in production, False in development
    app.config["JWT_COOKIE_CSRF_PROTECT"] = is_production  # True in production, False in development
    
    # Legacy routes keep insecure settings for backward compatibility
    app.config["JWT_COOKIE_SECURE_LEGACY"] = False
    app.config["JWT_COOKIE_CSRF_PROTECT_LEGACY"] = False
    
    app.config['JWT_SECRET_KEY'] = app.config['SECRET_KEY']
    
    app.config['FLASK_ADMIN_SWATCH'] = 'darkly'
    
    for key in overrides:
        app.config[key] = overrides[key]