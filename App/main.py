import os
from flask import Flask, render_template, redirect, url_for, jsonify
from flask_uploads import DOCUMENTS, IMAGES, TEXT, UploadSet, configure_uploads
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from datetime import datetime

from App.database import init_db, db
from dotenv import load_dotenv
from flask_migrate import Migrate
from App.config import load_config
from App.controllers import (
    setup_jwt,
    add_auth_context
)
from App.views import views, setup_admin

def add_views(app):
    for view in views:
        app.register_blueprint(view)

def register_api_v2(app):
    """Register API v2 blueprint for frontend integration"""
    try:
        from App.views.api_v2 import register_api_v2
        register_api_v2(app)
    except ImportError as e:
        app.logger.warning(f"API v2 not available: {e}")

def create_app(overrides={}):
    # Load environment variables from .env if present
    load_dotenv()
    app = Flask(__name__, static_url_path='/static')
    load_config(app, overrides)
    
    # Configure CORS for API endpoints - allow frontend origins
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://localhost:3001",  # Next.js dev server
                "http://127.0.0.1:3001",
                "https://help-desk-rostering-lybtet35y-firepenguindisopandas-projects.vercel.app",
                "https://help-desk-rostering.vercel.app"
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })
    
    add_auth_context(app)
    photos = UploadSet('photos', TEXT + DOCUMENTS + IMAGES)
    configure_uploads(app, photos)
    
    # Add custom filters - this is the key fix
    @app.template_filter('datetime')
    def format_datetime(value, format='%B %d, %Y, %I:%M %p'):
        """Format a datetime object to a readable string."""
        if value is None:
            return ""
        return value.strftime(format)
    
    add_views(app)
    register_api_v2(app)  # Register API v2 endpoints for frontend
    init_db(app)
    # Initialize migration extension early so Alembic env can access metadata
    Migrate(app, db)
    jwt = setup_jwt(app)
    setup_admin(app)
    
    # Create database tables if they don't exist (safer approach)
    with app.app_context():
        try:
            # Use CREATE TABLE IF NOT EXISTS approach via inspector
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            # Only create tables that don't exist
            tables_to_create = []
            for table_name, table in db.metadata.tables.items():
                if table_name not in existing_tables:
                    tables_to_create.append(table_name)
            
            if tables_to_create:
                db.create_all()
                print(f"Database tables created successfully: {', '.join(tables_to_create)}")
            else:
                print("All database tables already exist")
                
        except Exception as e:
            print(f"Database setup info: {e}")
            # Try the fallback approach for compatibility
            try:
                db.create_all()
                print("Database tables created using fallback method")
            except Exception as fallback_e:
                print(f"Warning: Database table creation issue: {fallback_e}")
                # Continue anyway - app might still work with existing tables

    # --- Hardened /healthcheck endpoint ---
    @app.get("/healthcheck")
    def healthcheck():
        checks = {}
        overall_ok = True
        now = datetime.utcnow().isoformat() + "Z"
        checks['app'] = {'ok': True, 'time': now}

        # Config sanity
        missing = []
        required = ['SECRET_KEY']
        for k in required:
            if not app.config.get(k):
                missing.append(k)
        if missing:
            checks['config'] = {'ok': False, 'missing': missing}
            overall_ok = False
        else:
            checks['config'] = {'ok': True}

        # Uploads directory writable
        upload_path = (
            app.config.get('UPLOADED_PHOTOS_DEST') or
            app.config.get('UPLOADS_DEFAULT_DEST') or
            app.config.get('UPLOAD_FOLDER') or
            app.config.get('MEDIA_ROOT')
        )
        if upload_path:
            try:
                os.makedirs(upload_path, exist_ok=True)
                if os.access(upload_path, os.W_OK):
                    checks['uploads'] = {'ok': True, 'path': upload_path}
                else:
                    checks['uploads'] = {'ok': False, 'path': upload_path, 'error': 'not writable'}
                    overall_ok = False
            except Exception as e:
                checks['uploads'] = {'ok': False, 'error': str(e)}
                overall_ok = False
        else:
            checks['uploads'] = {'ok': False, 'error': 'no upload path configured'}
            overall_ok = False

        # Lightweight DB probe if a DB URI is configured
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL')
        if db_uri:
            try:
                # lazy import to avoid hard dependency until runtime
                from sqlalchemy import create_engine, text
                engine = create_engine(db_uri, pool_pre_ping=True, connect_args={})
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                checks['db'] = {'ok': True}
            except Exception as e:
                checks['db'] = {'ok': False, 'error': str(e)}
                overall_ok = False
        else:
            # If you intentionally run without DB, treat as skipped.
            checks['db'] = {'ok': True, 'skipped': True, 'note': 'no DB URI configured'}

        # JWT quick config check (light check)
        if app.config.get('JWT_SECRET_KEY') or app.config.get('JWT_PUBLIC_KEY'):
            checks['jwt'] = {'ok': True}
        else:
            checks['jwt'] = {'ok': False, 'error': 'JWT not configured'}
            # not fatal if your app does not use JWT at runtime; adjust as needed
            # overall_ok = False

        status_code = 200 if overall_ok else 503
        app.logger.info("healthz result: %s", checks)
        return jsonify(status='ok' if overall_ok else 'fail', checks=checks), status_code
    # --- end healthz ---
    
    @jwt.invalid_token_loader
    @jwt.unauthorized_loader
    def custom_unauthorized_response(error):
        return render_template('errors/401.html', error=error), 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_data):
        return redirect(url_for('auth_views.login_page'))
    
    app.app_context().push()
    return app