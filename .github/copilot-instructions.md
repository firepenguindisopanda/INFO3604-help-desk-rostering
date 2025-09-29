# Copilot Instructions for INFO3604 Help Desk Rostering

These notes orient AI coding agents to this Flask codebase so you can ship useful changes quickly and safely.

## Architecture
- App Factory: `App.main.create_app(overrides={})` builds the Flask app, loads config via `App.config.load_config`, initializes DB/JWT/CORS, registers blueprints, and adds a `/healthcheck` route.
- Views: Classic server-rendered blueprints live in `App/views/*.py`. API v2 lives under `App/views/api_v2/` and is registered by `register_api_v2(app)` (called inside `create_app`).
- Controllers/Models: Business logic in `App/controllers/**` and SQLAlchemy models in `App/models/**`. Prefer calling controllers from views instead of touching models directly.
- Database: `App/database.py` provides `db` (SQLAlchemy) and `init_db`. Migrations use Flask-Migrate/Alembic (`migrations/`). SQLite FKs are enforced via an engine `connect` event.
- WSGI/CLI: `wsgi.py` constructs the app and defines CLI groups: `flask init`, `flask user ...`, `flask seed ...`, `flask test app ...`.

## Run & Debug
- Dev server (explicit app module):
  - PowerShell: `flask --app wsgi run`
  - Or via npm: `npm run serve` (requires Flask tooling on PATH)
- Health check: `GET /healthcheck` validates config, uploads path, DB, and JWT.
- Config: `App/default_config.py` or `App/custom_config.py` + env (`app.config.from_prefixed_env()`). DB URIs are normalized (postgres:// → postgresql://). Key envs: `SECRET_KEY`, `SQLALCHEMY_DATABASE_URI` (or `DATABASE_URL`).

## Database & Migrations
- Initialize DB tables on first run: `flask init` (also creates schema via controllers). App also calls `db.create_all()` on startup as a fallback.
- Alembic is wired via Flask-Migrate; use standard commands:
  - `flask db migrate -m "message"`
  - `flask db upgrade`

## Testing
- Pytest is configured in `pytest.ini` with `testpaths = App/tests`.
  - All tests: `flask test app all` (delegates to `pytest`).
  - Unit tests: `flask test app unit` (filters `-k UnitTests`). Ensure unit tests include `UnitTests` in their node name/marker.
  - Integration: `flask test app int` (filters `-k IntegrationTests`).
  - To run root-level ad hoc tests (outside `App/tests`), invoke with a path: `python -m pytest test_api_v2.py`.
- E2E (requires running server): `npm run e2e` (Mocha/Puppeteer, see `e2e/test.js`).

## Seed Data & Fixtures
- Sample CSVs in `sample/` seed courses and assistants:
  - Courses: `flask seed courses --limit 100`
  - Help Desk: `flask seed helpdesk --count 20`
  - Lab: `flask seed lab --count 20`
  - Reset sample data: `flask seed reset --type helpdesk|lab|all`

## API v2 Conventions
- Blueprint: `App/views/api_v2/__init__.py` defines `api_v2 = Blueprint('api_v2', __name__, url_prefix='/api/v2')` and `register_api_v2(app)`.
- Response helpers: Use `api_success(data=..., message=...)` and `api_error(message=..., status=...)` from `App/views/api_v2/utils.py` for consistent envelopes (see `API_V2_README.md`).
- Auth: JWT via Flask-JWT-Extended; endpoints expecting auth should read identity from JWT context. CORS allows the listed Next.js origins only—update in `App/main.py` if frontend origin changes.
- Example route (pattern):
  ```python
  from App.views.api_v2 import api_v2
  from App.views.api_v2.utils import api_success, api_error, validate_json_request

  @api_v2.route('/courses', methods=['POST'])
  def create_course_route():
      body, err = validate_json_request(required=['code','name'])
      if err: return api_error(err, status=400)
      course = controllers.course.create_course(body['code'], body['name'])
      return api_success(course.to_dict(), message='Created', status=201)
  ```

## Patterns & Tips
- Prefer controllers: Keep view functions thin; import functions from `App.controllers.*` to perform work.
- Time and schedule logic: Use helpers in `App/utils/time_utils.py` and scheduling endpoints in `App/views/api_v2/schedule.py`. OR-Tools (`ortools`) is available for roster generation.
- File uploads: Use `flask-reuploaded` with destination `App/uploads`. Registration expects `multipart/form-data` (see `auth.register`).
- Admin UI: Flask-Admin is initialized via `setup_admin(app)` in `create_app`.

## Deployment
- Gunicorn entry: `gunicorn -c gunicorn_config.py wsgi:app` (see `package.json` and `render.yaml`).
- Render.com: Service health check at `/healthcheck`; environment uses `FLASK_APP=wsgi.py` and `DATABASE_URL`.

If anything above is unclear or missing (e.g., preferred test markers, API v2 utilities), tell us and we’ll refine these instructions.