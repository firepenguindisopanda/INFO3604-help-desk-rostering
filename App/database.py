from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlite3 import Connection as SQLite3Connection

db = SQLAlchemy()

# Apply pragmatic settings to make SQLite behave closer to PostgreSQL when used.
# This runs for every new DB-API connection created by SQLAlchemy's Engine.
@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):  # pragma: no cover - simple setup code
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        # Referential integrity
        cursor.execute("PRAGMA foreign_keys=ON;")
        # Concurrency & durability trade-offs (WAL improves read concurrency)
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        # Behavioral alignment
        cursor.execute("PRAGMA case_sensitive_like=ON;")
        cursor.execute("PRAGMA recursive_triggers=ON;")
        # Performance tuning (safe, moderate values)
        cursor.execute("PRAGMA temp_store=MEMORY;")
        cursor.execute("PRAGMA cache_size=-64000;")  # 64MB cache (in KiB, negative means size in KiB)
        # Lock wait handling
        cursor.execute("PRAGMA busy_timeout=60000;")  # 60s
        cursor.close()

def get_migrate(app):
    return Migrate(app, db)

def create_db():
    db.create_all()
    
def init_db(app):
    db.init_app(app)