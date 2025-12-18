# Copilot Instructions: Help Desk Rostering System

## Project Overview
A Flask-based scheduling system for university Help Desk and Lab Assistant management. Uses **linear programming optimization** (PuLP) or (Google OR-Tools) to generate fair schedules with course coverage constraints, time tracking, and volunteer management.

## Architecture: Hybrid MVC + Dual API Pattern

### Core Structure
- **Models** (`App/models/`): SQLAlchemy ORM entities (User, Schedule, Shift, HelpDeskAssistant, LabAssistant, etc.)
- **Controllers** (`App/controllers/`): Business logic functions (create/get/update operations)
- **Views** (`App/views/`): Flask Blueprints
  - **Traditional routes**: Jinja2 template rendering for web UI
  - **API v2** (`App/views/api_v2/`): RESTful JSON endpoints for Next.js frontend
- **Services** (`App/services/`): Complex operations (SchedulingService, DataTransformationService)

### Key Principle: MVC Separation
**ALWAYS call controller functions from views** - never import models directly in views. Example:
```python
#  CORRECT
from App.controllers.student import get_student_by_id
student = get_student_by_id(student_id)

#  WRONG - avoid in views
from App.models import HelpDeskAssistant
student = HelpDeskAssistant.query.get(student_id)
```

## Critical Components

### 1. Scheduling Engine (`scheduler_lp/`)
Framework-agnostic PuLP-based optimizer. Can run in notebooks or CLI without Flask.

**Running standalone scheduler:**
```powershell
python -m scheduler_lp.examples
```

**Key fairness constraints:**
- Baseline hours target: 6 hours/assistant (bounded by availability)
- Penalty structure enforces: baseline satisfaction > shift coverage > fair extra distribution
- `max_extra_var` minimizes unfair hour allocation beyond baselines

**Integration point:** `App/services/scheduling_service.py` transforms DB models -> scheduler format -> DB persistence.

### 2. Database Management

**Environment precedence** (first non-empty wins):
1. `DATABASE_URI_SQLITE`
2. `DATABASE_URI_POSTGRES_LOCAL`
3. `DATABASE_URI_NEON`
4. `DATABASE_URL`
5. `SQLALCHEMY_DATABASE_URI`

**Migration workflow:**
```powershell
flask db migrate -m "description"  # Create migration
flask db upgrade                   # Apply migration
flask db downgrade                 # Rollback if needed
```

**Production data sync:**
```powershell
python scripts/sync_neon_to_local.py --source-url <neon> --target-url <local>
```

### 3. Authentication Pattern

**Dual JWT configuration** (legacy vs. API v2):
- **Legacy routes**: `JWT_COOKIE_SECURE_LEGACY=False`, `JWT_COOKIE_CSRF_PROTECT_LEGACY=False`
- **API v2**: Enforces secure cookies in production (`ENV=production`)

**Authorization decorators:**
```python
@jwt_required()           # Any authenticated user
@admin_required           # Admin only (stacks with @jwt_required())
@jwt_required_secure()    # API v2 secure mode
```

### 4. Time Zone Handling
**ALWAYS use Trinidad time (UTC-4)** for all scheduling operations:
```python
from App.utils.time_utils import trinidad_now, convert_to_trinidad_time
now = trinidad_now()  # Returns naive datetime in UTC-4
```

## Testing Strategy

### Running Tests
```powershell
pytest                          # All tests
pytest -m unit                  # Unit tests only
pytest -m integration           # Integration tests
pytest -m api_v2                # API v2 tests
pytest --cov=App                # With coverage
```

### Test Markers (setup.cfg)
- `@pytest.mark.unit` - Fast, isolated logic tests
- `@pytest.mark.integration` - Database/multi-component tests
- `@pytest.mark.api_v2` - API v2 endpoint tests
- `@pytest.mark.performance` - Benchmarks

### Load Testing
```powershell
locust -f App/tests/load_testing.py --host=http://localhost:8080
```

## Development Workflows

### Initial Setup
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
flask db upgrade
flask init  # Initialize with admin accounts (user: a, pass: 123)
flask run
```

### Docker Development
```powershell
# Start services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Structured Logging
Use structured logging with event types for observability:
```python
app.logger.info(
    'Operation completed',
    extra={
        'event': 'schedule_generated',
        'schedule_id': schedule.id,
        'duration_ms': elapsed,
    }
)
```

### Performance Monitoring
Wrap expensive operations with `@performance_monitor`:
```python
from App.utils.performance_monitor import performance_monitor

@performance_monitor("operation_name", log_slow_threshold=2.0)
def expensive_operation():
    # Automatically logs duration and warnings for slow operations
    pass
```

## Project-Specific Conventions

### Blueprint Registration
All blueprints defined in `App/views/__init__.py` with `views` list. API v2 registered separately via `register_api_v2()` in `App/main.py`.

### File Upload Locations
- Profile pictures: `App/static/uploads/`
- Transcripts: `App/uploads/transcripts/`
- Use `secure_filename()` for all user uploads

### Environment Variables
- Development: `.env` file (loads via python-dotenv)
- Docker: `.env.docker` file
- Never commit secrets - use `.env.example` as template

### Database Pool Configuration
**PostgreSQL**: `pool_pre_ping=True`, `pool_recycle=280` for connection resilience
**SQLite**: Pool options stripped in tests to avoid conflicts

### API Response Format
API v2 uses consistent JSON structure:
```python
{
    "success": true,
    "data": {...},
    "message": "Optional message"
}
```

## API v2 Migration Guide

### Migration Status
See `api_v2_conversion_status.md` for complete status. **Priority**: Time tracking, request management, user management routes.

### Conversion Pattern

**Legacy route structure:**
```python
# App/views/requests.py
@requests_views.route('/api/requests/<int:request_id>/approve', methods=['POST'])
@jwt_required()
@admin_required
def approve_request_endpoint(request_id):
    # Direct model queries, mixed response formats
    request = Request.query.get(request_id)
    return jsonify({"message": "Approved"}), 200
```

**API v2 structure:**
```python
# App/views/api_v2/requests.py (to be created)
from App.views.api_v2 import api_v2
from App.views.api_v2.utils import api_success, api_error, jwt_required_secure
from App.controllers.request import get_request_by_id, approve_request

@api_v2.route('/requests/<int:request_id>/approve', methods=['POST'])
@jwt_required_secure()  # Enforces secure JWT in production
def approve_request_api(request_id):
    """Approve a shift change request (admin only)"""
    # Use controllers, not models
    result = approve_request(request_id)
    if not result:
        return api_error("Request not found or already processed", status_code=404)
    
    # Consistent response format
    return api_success(
        data={"request": result.to_dict()},
        message="Request approved successfully"
    )
```

### Key Conversion Principles

1. **Use helper functions** from `App/views/api_v2/utils.py`:
   - `api_success(data, message, status_code)` - Consistent success responses
   - `api_error(message, errors, status_code)` - Consistent error responses
   - `validate_json_request(request)` - JSON validation with error handling
   - `jwt_required_secure()` - JWT authentication for API v2 (production-safe)

2. **URL structure changes**:
   - Legacy: `/api/requests/<id>/approve`
   - API v2: `/api/v2/requests/<id>/approve`
   - Auto-prefixed via `api_v2` Blueprint (`url_prefix='/api/v2'`)

3. **Authentication decorators**:
   - Use `@jwt_required_secure()` for API v2 (enforces HTTPS in production)
   - Legacy `@jwt_required()` + `@admin_required` still works but less secure

4. **Controller-first approach**:
   ```python
   #  WRONG - Don't query models in API v2 views
   from App.models import Request
   request = Request.query.get(request_id)
   
   #  CORRECT - Use controllers
   from App.controllers.request import get_request_by_id
   request = get_request_by_id(request_id)
   ```

5. **Response format standardization**:
   ```python
   #  Success response structure
   {
       "success": true,
       "data": {...},
       "message": "Optional message"
   }
   
   #  Error response structure
   {
       "success": false,
       "message": "Error description",
       "errors": {...}  // Optional detailed errors
   }
   ```

### Routes Still Needing Migration

** MIGRATION COMPLETE - All Core Routes Migrated!**

All high-priority routes have been successfully migrated to API v2:
-  Time tracking: Migrated to `/api/v2/volunteer/time-tracking/clock-in` and `/clock-out`
-  Request management: Migrated to `/api/v2/requests/*`
-  Password resets: Migrated to `/api/v2/password-resets/*`
-  User management: Migrated to `/api/v2/users/*`
-  Registration management: Migrated to `/api/v2/registrations/*`
-  Attendance reports: Migrated to `/api/v2/staff/<id>/attendance`
-  Available shifts/replacements: Migrated to `/api/v2/available-shifts` and `/api/v2/available-replacements`
-  Schedule configuration: Migrated to `/api/v2/schedule-config/*`
-  Performance monitoring: Migrated to `/api/v2/admin/performance/*`
-  Notifications: Migrated to `/api/v2/notifications/*`
-  Profile management: Migrated to `/api/v2/profiles/*`
-  Assistant management: Migrated to `/api/v2/assistants/*`
-  API Documentation: Available at `/api/v2/docs` and `/api/v2/openapi.json`

**Legacy endpoints remain available for backward compatibility with the HTML web interface.**

**Reference Implementation:**
See `App/views/api_v2/` directory for complete implementations. Key examples:
- `auth.py` - Authentication patterns
- `volunteer.py` - Time tracking implementation
- `requests.py` - Request management
- `schedule.py` - Schedule management
- `schedule_config.py` - Configuration management
- `tracking.py` - Attendance and time tracking
- `docs.py` - OpenAPI specification and Swagger UI

## Common Pitfalls

1. **Don't mix naive/aware datetimes** - Use `trinidad_now()` for all schedule operations
2. **Never query models directly in views** - Use controllers
3. **Always use `@performance_monitor` for scheduling operations** - Helps identify bottlenecks
4. **Check `active=True` when querying assistants** - Inactive users shouldn't appear in schedules
5. **Baseline feasibility** - `scheduler_lp` validates total baseline <= capacity before solving
6. **CORS configured only for `/api/*`** - Traditional routes don't need CORS
7. **API v2 requires consistent response format** - Always use `api_success()` and `api_error()`
8. **File uploads in API v2** - Use `multipart/form-data`, accept file URLs for external storage (e.g., UploadThing)

## Key Files Reference

- `App/config.py` - Database URI precedence logic
- `App/main.py` - Application factory, logging setup, healthcheck endpoint
- `scheduler_lp/linear_scheduler.py` - Core optimization model (200+ lines)
- `App/services/scheduling_service.py` - Integration layer between Flask and scheduler
- `docs/helpdesk_schedule_fairness.md` - Fairness requirements specification
- `IMPLEMENTATION_SUMMARY.md` - Production readiness fixes history
- `API_V2_README.md` - Complete API v2 endpoint documentation
- `api_v2_conversion_status.md` - API v2 migration tracking and priorities
- `App/views/api_v2/utils.py` - API v2 helper functions (api_success, api_error, jwt_required_secure)
- `App/views/api_v2/auth.py` - Reference implementation for API v2 patterns
- `App/views/api_v2/volunteer.py` - Complete volunteer/time-tracking API v2 implementation

## CI/CD Pipeline

Multi-stage pipeline in `.github/workflows/dev.yml`:
1. **lint-and-format**: Black, isort, Flake8, Bandit security scanning
2. **test-multi-python**: Python 3.9/3.10/3.11 with PostgreSQL
3. **security-scan**: Safety, Semgrep, dependency checks
4. **performance-test**: Load testing with benchmarks
5. **docker-build**: Container build + healthcheck validation
6. **integration-test**: API v2 integration tests
7. **deployment-readiness**: Config validation

**Performance targets:**
- API reads: <500ms
- API writes: <1000ms
- Schedule generation: <30s
- 50 req/sec throughput, <5% error rate

## Admin Accounts (Development)
After `flask init`:
- Help Desk Admin: username `a`, password `123`
- Lab Assistant Admin: username `b`, password `123`

Use `SKIP_HELP_DESK_SAMPLE=true` to skip sample data and allow self-registration.
