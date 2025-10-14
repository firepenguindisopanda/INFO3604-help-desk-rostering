import os
import uuid
from time import perf_counter
from flask import Flask, render_template, redirect, url_for, jsonify, request, g
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
from App.views import views
from App.logging_config import configure_logging

def add_views(app):
    for view in views:
        app.register_blueprint(view)

def register_api_v2(app):
    """Register API v2 blueprint for frontend integration"""
    try:
        from App.views.api_v2 import register_api_v2
        register_api_v2(app)
    except ImportError as e:
        app.logger.warning(
            'API v2 not available',
            extra={'event': 'api_registration_failed', 'error': str(e)},
        )

def create_app(overrides={}):
    # Load environment variables from .env if present
    load_dotenv()
    app = Flask(__name__, static_url_path='/static')
    load_config(app, overrides)

    configure_logging(app)
    app.logger.info(
        'Flask application configured',
        extra={
            'event': 'app_boot',
            'environment': app.config.get('ENV'),
            'debug': app.debug,
            'service': app.config.get('SERVICE_NAME', 'info3604-help-desk-rostering'),
        },
    )

    @app.before_request
    def _structured_request_logging() -> None:
        g.request_timer = perf_counter()
        g.request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        app.logger.info(
            'Incoming request',
            extra={
                'event': 'request_started',
                'request_id': g.request_id,
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_agent': request.user_agent.string,
            },
        )

    @app.after_request
    def _structured_response_logging(response):
        duration_ms = None
        if hasattr(g, 'request_timer'):
            duration_ms = round((perf_counter() - g.request_timer) * 1000, 2)
        request_id = getattr(g, 'request_id', None)
        if request_id:
            response.headers['X-Request-ID'] = request_id
        app.logger.info(
            'Completed request',
            extra={
                'event': 'request_completed',
                'request_id': request_id,
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration_ms': duration_ms,
            },
        )
        return response

    @app.teardown_request
    def _structured_request_teardown(exc):
        if exc is not None:
            request_id = getattr(g, 'request_id', None)
            app.logger.exception(
                'Unhandled request exception',
                extra={
                    'event': 'request_exception',
                    'request_id': request_id,
                    'method': getattr(request, 'method', None),
                    'path': getattr(request, 'path', None),
                },
            )
    
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
                app.logger.info(
                    'Database tables created',
                    extra={
                        'event': 'db_schema_sync',
                        'tables': tables_to_create,
                        'mode': 'initial',
                    },
                )
            else:
                app.logger.info(
                    'Database tables already exist',
                    extra={
                        'event': 'db_schema_sync',
                        'tables': [],
                        'mode': 'noop',
                    },
                )
                
        except Exception as e:
            app.logger.warning(
                'Database setup encountered an issue',
                extra={'event': 'db_schema_warning', 'error': str(e)},
            )
            # Try the fallback approach for compatibility
            try:
                db.create_all()
                app.logger.info(
                    'Database tables created using fallback method',
                    extra={'event': 'db_schema_sync', 'mode': 'fallback'},
                )
            except Exception as fallback_e:
                app.logger.error(
                    'Database table creation failed',
                    extra={
                        'event': 'db_schema_error',
                        'error': str(fallback_e),
                    },
                )
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
        app.logger.info(
            'Healthcheck completed',
            extra={
                'event': 'healthcheck_completed',
                'overall_ok': overall_ok,
                'checks': checks,
                'request_id': getattr(g, 'request_id', None),
            },
        )
        return jsonify(status='ok' if overall_ok else 'fail', checks=checks), status_code
    # --- end healthz ---
    
    @jwt.invalid_token_loader
    @jwt.unauthorized_loader
    def custom_unauthorized_response(error):
        app.logger.warning(
            'Unauthorized access attempt',
            extra={
                'event': 'security_auth_failure',
                'reason': error,
                'path': request.path,
                'request_id': getattr(g, 'request_id', None),
            },
        )
        return render_template('errors/401.html', error=error), 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_data):
        app.logger.info(
            'JWT token expired',
            extra={
                'event': 'security_token_expired',
                'identity': jwt_data.get('sub') if isinstance(jwt_data, dict) else None,
                'path': request.path,
                'request_id': getattr(g, 'request_id', None),
            },
        )
        return redirect(url_for('auth_views.login_page'))
    
    app.app_context().push()
    return app