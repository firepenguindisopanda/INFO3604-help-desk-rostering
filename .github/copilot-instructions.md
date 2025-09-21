# AI Coding Agent Guide for INFO3604 Help Desk Rostering

This repo is a Flask app that generates and manages rosters for two domains: "helpdesk" (Mon–Fri hourly shifts) and "lab" (Mon–Sat 4‑hour blocks). Use these instructions to be productive quickly.

## Architecture
- App factory: `App/main.py:create_app(overrides={})` wires config, JWT, blueprints, uploads, DB, and a `/healthcheck` route. `wsgi.py` instantiates `app` for Gunicorn.
- Layering:
  - Views (Flask blueprints, HTTP/UI): `App/views/*` (e.g., `auth.py`, `schedule.py`).
  - Controllers (business logic): `App/controllers/*` (e.g., `schedule.py`, `initialize.py`, `auth.py`).
  - Models (SQLAlchemy): `App/models/*` (e.g., `user.py`, `schedule.py`, `shift.py`, etc.).
  - Utilities: `App/utils/*` (time helpers, etc.).
- Scheduling engines: implemented in `App/controllers/schedule.py` using OR‑Tools CP‑SAT:
  - Helpdesk: hourly shifts, per‑course capacity via `shift_course_demand` table (raw SQL helpers `add_course_demand_to_shift`/`get_course_demands_for_shift`).
  - Lab: 4‑hour blocks with fairness objective `max L` and at least one experienced assistant per shift.
- JWT + roles: `App/controllers/auth.py` issues tokens; `App/middleware.py` enforces `admin_required` and `volunteer_required`. Admin `role` drives schedule type and UI filtering.
- DB & migrations: `App/database.py` exposes `db` and `get_migrate`; Flask‑Migrate is configured but migrations folder may need init.

## Developer Workflows
- Env and config:
  - Defaults in `App/default_config.py`; environment overrides via `App/config.py:load_config` and `from_prefixed_env()`.
  - DB URI resolution order: `DATABASE_URI_SQLITE` | `DATABASE_URI_NEON` | `DATABASE_URL` | default config. `postgres://` is normalized to `postgresql://`.
  - JWT uses `SECRET_KEY`; cookies + headers are enabled in dev.
- CLI commands (defined in `wsgi.py`):
  - `flask init` — drops/recreates tables and seeds admins and sample data (guarded by `SKIP_HELP_DESK_SAMPLE`).
  - `flask user create <username> <password>`; `flask user list [string|json]`.
  - Seeding: `flask seed courses [--limit N]`, `flask seed helpdesk [--count N]`, `flask seed lab [--count N]`, `flask seed reset [--type helpdesk|lab|all]`.
  - Tests: `flask test app [all|unit|int]` routes to pytest with markers/filters.
- Running locally:
  - Python: `flask run` (port via `FLASK_RUN_PORT`, default 8080 in README).
  - Gunicorn: `npm run prod-serve` or `gunicorn -c gunicorn_config.py wsgi:app` (binds `0.0.0.0:8080`).
  - Health: `GET /healthcheck` (extended) and `GET /health` (simple).
- Tests:
  - Unit/integration tests live in `App/tests/`; pytest settings in `pytest.ini` (`testpaths = App/tests`).
  - Common pattern: `create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'}); create_db()` in `setUp`.
  - Performance tests with Locust: `locust -f App/tests/test_performance.py --host=http://localhost:8080`.
- E2E:
  - `npm run e2e` runs Mocha + Puppeteer Core (`e2e/test.js`) assuming server at `http://localhost:8080`.

## Admin UI & Flows
- Admin panel: Flask-Admin at `/admin/` secured via JWT (`App/views/admin.py:SecureAdminIndexView`, `AdminView`).
- Schedule management: `/schedule` page; JSON APIs under `/api/schedule/*` (generate, save, publish, clear, pdf). Role (`helpdesk|lab`) alters day/time parsing and shift length.
- Requests console: `/requests` (shift change approvals), `/registrations` (volunteer onboarding), `/password-resets` (account recovery). All require `@admin_required`.
- Tracking dashboard: `/timeTracking` shows staff KPIs; related APIs under `/api/staff/*` for attendance reports and marking missed shifts.
- Profiles: `/profile` lists assistants; `/admin/staff/<username>/profile` shows detailed staff view with editing via APIs.

## Conventions & Patterns
- Blueprints are collected in `App/views/__init__.py` and registered via `add_views` inside `create_app`.
- Schedule IDs: `1` for helpdesk, `2` for lab. Many controller/view functions assume this mapping.
- Helpdesk shift generation creates Mon–Fri hourly slots 9–17; lab generates Mon–Sat blocks at 8, 12, 16.
- Role‑aware behavior: Admin `role` (`helpdesk`|`lab`) determines schedule type, allowed endpoints (`@admin_required`), and time parsing (`parse_time_to_hour`).
- Raw SQL is used for `shift_course_demand` via `sqlalchemy.text(...)`. Keep parameters bound.
- Templates rely on a custom Jinja filter: `datetime` defined in `create_app`.
- Static uploads directory is configured by `UPLOADED_PHOTOS_DEST` → `App/uploads`.

## SQLite vs PostgreSQL
- Configure SQLite to mimic Postgres constraints to avoid switching issues:
  - Use `sqlite:///...?...` with `foreign_keys=on` (already set in `App/default_config.py`). Ensure PRAGMA foreign_keys is respected in tests.
  - Avoid vendor-specific SQL except where already isolated: raw SQL for `shift_course_demand` uses `sqlalchemy.text` with bound params — keep that pattern.
  - Stick to explicit `DateTime` columns and consistent timezone handling (`App/utils/time_utils.py`).
  - For LIKE/ILIKE differences, prefer SQLAlchemy filters or normalize data for case-insensitive comparisons.

## Key Files
- App entry: `App/main.py`, `wsgi.py`.
- Auth & guards: `App/controllers/auth.py`, `App/middleware.py`, views in `App/views/auth.py`.
- Scheduling: `App/controllers/schedule.py`, admin views in `App/views/schedule.py`.
- Models: `App/models/schedule.py`, `App/models/shift.py`, `App/models/user.py`, and related domain models.
- Seed/init: `App/controllers/initialize.py`; CLI wiring in `wsgi.py`.

## Endpoint → Controller Map
- `/api/login` → `App/views/auth.py:user_login_api` → `App/controllers/auth.py:login`
- `/api/schedule/generate|save|clear|...` → `App/views/schedule.py` → `App/controllers/schedule.py`
- `/api/schedule/pdf` → `App/views/schedule.py:download_schedule_pdf` → `App/controllers/schedule.py:get_schedule_data`
- `/api/staff/available|check-availability|attendance|...` → `App/views/schedule.py` and `App/views/tracking.py` → `App/controllers/tracking.py`
- `/api/requests/*` → `App/views/requests.py` → `App/controllers/request.py`
- `/api/registrations/*` → `App/views/requests.py` → `App/controllers/registration.py`
- `/api/password-resets/*` → `App/views/requests.py` → `App/controllers/password_reset.py`
- `/api/notifications*` → `App/views/notification.py` → `App/controllers/notification.py`
- `/api/users` → `App/views/user.py` → `App/controllers/user.py`
- `/api/courses` → `App/views/volunteer.py` → `App/controllers/course.py`

## Role-Aware Behavior
- Admin vs Volunteer: Admin-only routes guarded by `@admin_required` in `App/middleware.py`; volunteers use `@volunteer_required` routes.
- Schedule type: Admin `role` (`helpdesk|lab`) determines generator path, time parsing, and shift length in `App/controllers/schedule.py`.
- Schedule IDs: Helpdesk is `1`, Lab is `2` across controllers/models.
- JWT transport: Cookies + Authorization header enabled in dev; APIs accept `Bearer <JWT>`.

## Common Tasks (Examples)
- Initialize fresh dev DB with admins and sample data:
  - `flask db init`; `flask db migrate -m "init"`; `flask db upgrade`; `flask init`
- Generate and publish schedules (as admin):
  - POST `/api/schedule/generate` with JSON `{ "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" }` and a valid JWT.
  - POST `/api/schedule/<id>/publish` or `/api/schedule/<id>/publish_with_sync`.
- Export current schedule as PDF:
  - GET `/api/schedule/pdf` (admin role selects helpdesk vs lab).

## cURL Examples
- Login (JWT in response body and cookies):
  - `curl -X POST http://localhost:8080/api/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin"}'`
- Generate schedule (admin, role-scoped):
  - `curl -X POST http://localhost:8080/api/schedule/generate -H "Authorization: Bearer <JWT>" -H "Content-Type: application/json" -d '{"start_date":"2025-09-01","end_date":"2025-09-30"}'`
- Publish schedule by ID:
  - `curl -X POST http://localhost:8080/api/schedule/1/publish -H "Authorization: Bearer <JWT>"`
- Attendance report (admin):
  - `curl -X GET "http://localhost:8080/api/staff/attendance?start=2025-09-01&end=2025-09-30" -H "Authorization: Bearer <JWT>"`
- Download schedule PDF:
  - `curl -L -X GET http://localhost:8080/api/schedule/pdf -H "Authorization: Bearer <JWT>" -o schedule.pdf`

## Deployment Notes
- Dockerfile installs extra system libs (WeasyPrint, gevent, MySQL/Postgres headers). Gunicorn binds `:8080` but Dockerfile `EXPOSE` is `8085` (mismatch). Runtime uses `wsgi:app`.
- Env vars to set in production: `SECRET_KEY`, `SQLALCHEMY_DATABASE_URI` (or supported aliases), JWT cookie security flags, and uploads destination if needed.

## When Modifying Code
- Maintain schedule ID/type invariants and role‑based branching.
- Prefer adding new blueprints to `App/views/__init__.py` and register via `add_views`.
- For DB schema changes, use Flask‑Migrate workflow (`flask db migrate`, `flask db upgrade`).
- Keep `shift_course_demand` helpers using `sqlalchemy.text` to avoid dialect issues.

Questions or unclear sections? Tell me where you need more specifics (e.g., migration setup, JWT cookies in local tests, or e2e expectations), and I’ll refine this doc.