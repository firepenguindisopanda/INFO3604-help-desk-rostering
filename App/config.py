import os
from datetime import timedelta

POSTGRES_SCHEME = 'postgres://'
POSTGRESQL_SCHEME = 'postgresql://'

def load_config(app, overrides):
    if os.path.exists(os.path.join('./App', 'custom_config.py')):
        app.config.from_object('App.custom_config')
    else:
        app.config.from_object('App.default_config')
    
    app.config.from_prefixed_env()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    app.config['UPLOADED_PHOTOS_DEST'] = "App/static/uploads"
    
    db_url = (
        os.environ.get('DATABASE_URI_NEON') or
        os.environ.get('DATABASE_URI_SQLITE') or
        os.environ.get('DATABASE_URI_POSTGRES_LOCAL') or
        app.config.get('SQLALCHEMY_DATABASE_URI')
    )
    if db_url:
        if db_url.startswith(POSTGRES_SCHEME):
            db_url = db_url.replace(POSTGRES_SCHEME, POSTGRESQL_SCHEME, 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
        print(f"Using database URI: {db_url}")
    else:
        print("Warning: No database URI configured")

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

    # Normalize DB URI if overrides replaced it (e.g., postgres scheme)
    final_db_uri = app.config.get('SQLALCHEMY_DATABASE_URI') or ''
    if final_db_uri.startswith(POSTGRES_SCHEME):
        final_db_uri = final_db_uri.replace(POSTGRES_SCHEME, POSTGRESQL_SCHEME, 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = final_db_uri

    # Ensure SQLAlchemy re-establishes dropped connections (e.g., idle Postgres SSL timeouts)
    engine_options = app.config.setdefault('SQLALCHEMY_ENGINE_OPTIONS', {})
    if final_db_uri.startswith('sqlite'):
        # SQLite doesn't use the connection pool in the same way; avoid pool options that break tests
        for key in ('pool_pre_ping', 'pool_recycle', 'pool_timeout'):
            engine_options.pop(key, None)
    else:
        engine_options.setdefault('pool_pre_ping', True)
        engine_options.setdefault('pool_recycle', 280)
        engine_options.setdefault('pool_timeout', 30)