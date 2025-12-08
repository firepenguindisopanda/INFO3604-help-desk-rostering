from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlite3 import Connection as SQLite3Connection

db = SQLAlchemy()

def get_migrate(app):
    return Migrate(app, db)

def create_db():
    db.create_all()
    _reset_user_query()
    
def init_db(app):
    db.init_app(app)


def _reset_user_query():
    """Restore User.query if earlier tests patched it (e.g., MagicMock)."""
    try:
        from unittest.mock import MagicMock
        from App.models import User

        if isinstance(getattr(User, 'query', None), MagicMock):
            User.query = db.session.query_property()
    except Exception:
        # Defensive: never break create_db if imports fail
        return

@event.listens_for(Engine, "connect")
def _enable_sqlite_fk(dbapi_connection, connection_record):
    # Only apply for the sqlite3 DBAPI (file or in-memory)
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()