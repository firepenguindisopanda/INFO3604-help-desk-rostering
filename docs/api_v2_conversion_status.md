# API v2 Implementation Status

This document compares the current API v2 routes with the classic routes that need to be converted.

## Implemented in API v2

### Authentication Routes (`/api/v2/auth/`)
- `POST /api/v2/auth/login` - User login with JWT token
- `POST /api/v2/auth/register` - User registration (JSON with profile_picture_url and transcript_url)
- `POST /api/v2/auth/logout` - User logout (client-side token removal)

### User Profile Routes (`/api/v2/`)
- `GET /api/v2/me` - Get current authenticated user's profile
- `PUT /api/v2/me` - Update current user's profile information

### Admin Routes (`/api/v2/admin/`)
- `GET /api/v2/admin/dashboard` - Admin dashboard with schedules, attendance, and pending items
- `GET /api/v2/admin/stats` - Detailed administrative statistics

### Schedule Management Routes (`/api/v2/admin/schedule/`)
- `POST /api/v2/admin/schedule/generate` - Generate a new schedule
- `GET /api/v2/admin/schedule/current` - Get current active schedule
- `GET /api/v2/admin/schedule/details` - Get detailed schedule info by ID
- `POST /api/v2/admin/schedule/save` - Save schedule changes and assignments
- `POST /api/v2/admin/schedule/clear` - Clear existing schedule and assignments
- `POST /api/v2/admin/schedule/<int:schedule_id>/publish` - Publish a schedule
- `POST /api/v2/admin/schedule/<int:schedule_id>/publish-with-sync` - Publish with data sync and notifications

### Staff Management Routes (`/api/v2/admin/schedule/staff/`)
- `GET /api/v2/admin/schedule/staff/available` - Get staff available for specific day/time
- `GET /api/v2/admin/schedule/staff/check-availability` - Check if specific staff is available
- `POST /api/v2/admin/schedule/staff/check-availability/batch` - Batch availability check
- `POST /api/v2/admin/schedule/staff/remove` - Remove staff from specific shift

### Schedule Export Routes (`/api/v2/admin/schedule/`)
- `GET /api/v2/admin/schedule/export/pdf` - Export current schedule as PDF
- `GET /api/v2/admin/schedule/summary` - Get schedule summary statistics

### Student Routes (`/api/v2/student/`)
- `GET /api/v2/student/dashboard` - Student dashboard with upcoming shifts and activity
- `GET /api/v2/student/schedule` - Get student's full schedule for date range

### Course Management Routes (`/api/v2/courses/`)
- `GET /api/v2/courses` - Get all available courses
- `POST /api/v2/courses` - Create a new course (admin only)
- `GET /api/v2/courses/<string:code>` - Get specific course by code
- `PUT /api/v2/courses/<string:code>` - Update course (admin only)
- `DELETE /api/v2/courses/<string:code>` - Delete course (admin only)

### Request Management Routes (`/api/v2/requests/`) **NEW**
- `GET /api/v2/requests` - Get all requests (admin) or user's requests (student)
- `POST /api/v2/requests` - Submit new shift change request (volunteers only)
- `POST /api/v2/requests/<int:request_id>/approve` - Approve shift change request (admin only)
- `POST /api/v2/requests/<int:request_id>/reject` - Reject shift change request (admin only)
- `POST /api/v2/requests/<int:request_id>/cancel` - Cancel pending request (volunteers only)
- `GET /api/v2/available-shifts` - Get available shifts for student requests
- `GET /api/v2/available-replacements` - Get available replacement assistants

### Time Tracking Routes (`/api/v2/staff/`) **NEW**
- `GET /api/v2/staff/<staff_id>/attendance` - Get attendance records for specific staff
- `POST /api/v2/staff/<staff_id>/mark-missed` - Mark shift as missed
- `POST /api/v2/staff/attendance/report` - Generate attendance report
- `GET /api/v2/staff/attendance/summary` - Get attendance summary statistics

### User Management Routes (`/api/v2/users/`)  **NEW**
- `GET /api/v2/users` - Get all users (admin only)
- `POST /api/v2/users` - Create new user (admin only)
- `GET /api/v2/users/<username>` - Get specific user by username (admin only)
- `POST /api/v2/users/<username>/activate` - Activate user account (admin only)
- `GET /api/v2/users/search` - Search users by criteria (admin only)

### Password Reset Management Routes (`/api/v2/password-resets/`)  **NEW**
- `GET /api/v2/password-resets` - Get all password reset requests (admin only)
- `POST /api/v2/password-resets/<int:reset_id>/complete` - Complete password reset (admin only)
- `POST /api/v2/password-resets/<int:reset_id>/reject` - Reject password reset (admin only)
- `GET /api/v2/password-resets/<int:reset_id>` - Get specific reset request details (admin only)
- `GET /api/v2/password-resets/pending` - Get only pending reset requests (admin only)

### Registration Management Routes (`/api/v2/registrations/`)  **NEW**
- `GET /api/v2/registrations` - Get all registration requests (admin only)
- `POST /api/v2/registrations/<int:registration_id>/approve` - Approve registration request (admin only)
- `POST /api/v2/registrations/<int:registration_id>/reject` - Reject registration request (admin only)
- `GET /api/v2/registrations/<int:registration_id>` - Get specific registration details (admin only)
- `GET /api/v2/registrations/<int:registration_id>/transcript` - Get transcript information (admin only)
- `GET /api/v2/registrations/<int:registration_id>/transcript/download` - Download transcript file (admin only)
- `GET /api/v2/registrations/pending` - Get only pending registration requests (admin only)

### Notification Routes (`/api/v2/notifications/`)  **NEW**
- `GET /api/v2/notifications` - List notifications for current user
- `GET /api/v2/notifications/count` - Count unread notifications
- `POST /api/v2/notifications/<int:notification_id>/read` - Mark notification as read
- `POST /api/v2/notifications/read-all` - Mark all notifications as read
- `DELETE /api/v2/notifications/<int:notification_id>` - Delete a notification

### Profile Management Routes (`/api/v2/profiles/`)  **NEW**
- `GET /api/v2/profiles/staff/<username>` - Fetch staff profile (self or admin)
- `PUT /api/v2/profiles/staff/<username>` - Admin update of staff profile/capabilities
- `PUT /api/v2/profiles/students/<username>` - Admin update of student profile basics
- `GET /api/v2/profiles/admin` - Admin profile context

### Volunteer Time Tracking Routes (`/api/v2/volunteer/`) 
- `GET /api/v2/volunteer/dashboard` - Volunteer dashboard with shifts and schedule
- `GET /api/v2/volunteer/time-tracking` - Time tracking metrics and today's shift state
- `POST /api/v2/volunteer/time-tracking/clock-in` - Clock into current shift
- `POST /api/v2/volunteer/time-tracking/clock-out` - Clock out of active shift
- `GET /api/v2/volunteer/profile` - Get volunteer profile information
- `POST /api/v2/volunteer/availability` - Submit volunteer availability

### Schedule Configuration Routes (`/api/v2/schedule-config/`) **NEW**
- `GET /api/v2/schedule-config` - Get all schedule configurations
- `POST /api/v2/schedule-config` - Create new schedule configuration (admin only)
- `GET /api/v2/schedule-config/<int:config_id>` - Get specific configuration by ID
- `PUT /api/v2/schedule-config/<int:config_id>` - Update configuration (admin only)
- `DELETE /api/v2/schedule-config/<int:config_id>` - Delete configuration (admin only)
- `GET /api/v2/schedule-config/active` - Get currently active configuration
- `POST /api/v2/schedule-config/<int:config_id>/activate` - Activate a configuration
- `GET /api/v2/schedule-config/<int:config_id>/preview-shifts` - Preview shifts for configuration
- `POST /api/v2/schedule-config/default` - Create default configuration
- `GET /api/v2/schedule-config/summary` - Get configuration summary statistics

### Schedule Query Routes (`/api/v2/schedules/`) **NEW**
- `GET /api/v2/schedules` - Get all schedules with filtering options

### Assistant Management Routes (`/api/v2/assistants/`, `/api/v2/admin/assistants/`) **NEW**
- `GET /api/v2/assistants` - Get all assistants (help desk and lab assistants)
- `DELETE /api/v2/admin/assistants/<username>` - Delete assistant and cascade related data (admin only)

### Performance Monitoring Routes (`/api/v2/admin/performance/`) **NEW**
- `GET /api/v2/admin/performance/metrics` - Get performance metrics summary (admin only)
- `GET /api/v2/admin/performance/slow-operations` - Get slow operations with optimization recommendations (admin only)
- `GET /api/v2/admin/performance/health` - Get system health check information (admin only)
- `POST /api/v2/admin/performance/log-summary` - Log performance summary (admin only)

### API Documentation Routes (`/api/v2/`) **NEW**
- `GET /api/v2/openapi.json` - Get OpenAPI 3.0 specification for all API v2 endpoints
- `GET /api/v2/docs` - Interactive Swagger UI documentation

## Not Yet Implemented in API v2 (LEGACY ROUTES STILL AVAILABLE)

### Legacy Authentication Routes (from `auth.py`) - DEPRECATED
- `POST /api/login` - Legacy login endpoint (use `/api/v2/auth/login` instead)
- `GET /api/identify` - User identification endpoint (functionality merged into `/api/v2/me`)

### Schedule Routes with Enhanced Functionality (from `schedule.py`)
- `POST /api/schedule/<int:schedule_id>/publish_with_sync` -  migrated to `/api/v2/admin/schedule/<id>/publish-with-sync`

## Routes with Enhanced API v2 Implementations

### Request Management
- **Legacy**: Various `/api/requests/*` endpoints with mixed response formats
- **API v2**: Standardized `/api/v2/requests/*` with consistent JSON responses and better error handling

### Time Tracking  
- **Legacy**: `/volunteer/time_tracking/clock_in`, `/volunteer/time_tracking/clock_out` 
- **API v2**: `/api/v2/volunteer/time-tracking/clock-in` and `/clock-out` with enhanced validation and response format

### User Management
- **Legacy**: Basic `/api/users` endpoints
- **API v2**: Full CRUD operations with `/api/v2/users/*` including search and activation

### Password Resets
- **Legacy**: Basic approve/reject functionality  
- **API v2**: Complete workflow management with `/api/v2/password-resets/*`

### Registration Management
- **Legacy**: Basic approve/reject with file handling
- **API v2**: Enhanced `/api/v2/registrations/*` with proper transcript management and metadata

## Migration Status Summary

### COMPLETED (100% API v2 Coverage)
- **Authentication**: Core login/register/logout functionality
- **User Profile Management**: Get and update user profiles
- **Course Management**: Full CRUD operations
- **Schedule Management**: Generation, publishing, staff management, export
- **Schedule Configuration**: Full CRUD for schedule configurations with activation and preview
- **Request Management**: All CRUD operations migrated
- **Time Tracking & Attendance**: Full admin reporting capabilities
- **User Management**: Complete user lifecycle management  
- **Password Reset Management**: Full workflow support
- **Registration Management**: Enhanced transcript handling
- **Volunteer Dashboard**: Time tracking and shift management
- **Notification Management**: Full notification lifecycle
- **Profile Management**: Staff and student profile management
- **Assistant Management**: List and delete assistants
- **Performance Monitoring**: Metrics, health checks, and slow operation tracking
- **API Documentation**: OpenAPI spec and interactive Swagger UI
- **Admin Dashboard**: Comprehensive admin statistics and insights
- **Student Dashboard**: Student-specific views and schedules

### LEGACY ENDPOINTS (Still Available for HTML Rendering)
All original routes in `/App/views/` continue to work for:
- **HTML Template Rendering**: Jinja2 templates for web UI
- **Form-based Interactions**: Traditional web forms
- **File Uploads**: Direct multipart/form-data handling
- **Page Navigation**: Traditional web application flow

The legacy routes serve the web interface while API v2 routes serve modern frontends (React, mobile apps, etc.).

## Routes with Different Implementations

### Schedule Current Route
- **Classic**: `GET /api/schedule/current` - Returns schedule with different formatting
- **API v2**: `GET /api/v2/admin/schedule/current` - Returns schedule with API v2 formatting

### Staff Availability Routes
- **Classic**: `GET /api/staff/available`, `GET /api/staff/check-availability`, `POST /api/staff/check-availability/batch`
- **API v2**: `GET /api/v2/admin/schedule/staff/available`, `GET /api/v2/admin/schedule/staff/check-availability`, `POST /api/v2/admin/schedule/staff/check-availability/batch`

## Conversion Priority

### ALL CORE FUNCTIONALITY COMPLETED
All high-priority and medium-priority routes have been successfully migrated to API v2:
- **Time Tracking**: Clock in/out, attendance reports, mark missed shifts
- **Request Management**: Approve/reject requests, submit requests, available shifts/replacements
- **Password Reset Management**: Complete/reject password resets
- **User Management**: Get/create/search/activate users
- **Registration Management**: Approve/reject registrations, transcript management
- **Schedule Publishing**: Enhanced publish with sync functionality
- **Schedule Configuration**: Full configuration management
- **Performance Monitoring**: Comprehensive performance tracking
- **Notification Management**: Complete notification workflow

### Low Priority (Optional Cleanup)
1. **Legacy Authentication**: `/api/login`, `/api/identify` - Can remain for backward compatibility
2. **Legacy Route Deprecation**: Consider adding deprecation warnings to old endpoints

## Implementation Notes

- All API v2 routes use consistent JSON response format with `api_success()` and `api_error()` helpers
- JWT authentication is required for protected routes using `@jwt_required_secure()`
- File uploads use `multipart/form-data` format for legacy compatibility
- Date parameters use `YYYY-MM-DD` format consistently
- Admin routes require admin role, volunteer routes require volunteer role
- Error handling includes proper HTTP status codes and detailed error messages
- All new endpoints follow design principles:
  - **Single Responsibility**: Each endpoint has one clear purpose
  - **Encapsulation**: Business logic is abstracted through controllers
  - **Loose Coupling**: Routes depend on abstractions, not concrete implementations
  - **Fail Fast**: Input validation happens immediately
  - **DRY**: Common validation and formatting logic is extracted into reusable functions
  - **Defensive Programming**: Comprehensive error handling and edge case management

## Architecture Benefits

### Hybrid Approach Advantages
1. **Backward Compatibility**: Existing web interface continues to work
2. **Modern API Support**: New frontends can use standardized REST API
3. **Gradual Migration**: Teams can migrate at their own pace
4. **Technology Flexibility**: Support for both traditional and modern architectures

### Code Quality Improvements
1. **Consistent Error Handling**: Standardized error responses across all API v2 endpoints
2. **Input Validation**: Comprehensive validation with clear error messages
3. **Security**: Enhanced JWT handling with production-safe defaults
4. **Maintainability**: Clear separation of concerns and modular design
5. **Testability**: Easy to test individual endpoints without complex setup
6. **Documentation**: Self-documenting code with clear function purposes</content>
<parameter name="filePath">api_v2_conversion_status.md