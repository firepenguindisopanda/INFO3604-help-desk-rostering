# API v2 Documentation

## Overview

This document describes the API v2 endpoints for the Help Desk Rostering application. These endpoints are designed to support a React/Next.js frontend and provide a clean separation between the backend API and frontend presentation.

**For a complete list of all implemented endpoints**, see [`api_v2_conversion_status.md`](api_v2_conversion_status.md) which provides:
- Complete endpoint inventory organized by category
- Migration status tracking
- Design principles and implementation notes

## Base URL

All API v2 endpoints are prefixed with `/api/v2/`

## Interactive Documentation

The **recommended way** to explore the API is through the interactive documentation:

- **Swagger UI**: Visit `/api/v2/docs` in your browser for interactive API documentation
- **OpenAPI Spec**: Get the raw OpenAPI 3.0 specification at `/api/v2/openapi.json`

These endpoints provide:
- Complete endpoint descriptions
- Request/response schemas
- Authentication requirements
- Try-it-out functionality
- Example requests and responses

## Endpoint Categories

API v2 provides comprehensive coverage across all application functionality:

### Core Features
- **Authentication** (`/api/v2/auth/*`) - Login, register, logout, profile management
- **Schedule Management** (`/api/v2/admin/schedule/*`) - Generate, publish, export schedules
- **Schedule Configuration** (`/api/v2/schedule-config/*`) - CRUD for schedule settings
- **Course Management** (`/api/v2/courses/*`) - Full course CRUD operations
- **Request Management** (`/api/v2/requests/*`) - Shift change requests
- **User Management** (`/api/v2/users/*`) - User lifecycle management

### Dashboards & Views
- **Admin Dashboard** (`/api/v2/admin/dashboard`) - Administrative overview
- **Student Dashboard** (`/api/v2/student/dashboard`) - Student-specific views
- **Volunteer Dashboard** (`/api/v2/volunteer/dashboard`) - Volunteer portal

### Time & Attendance
- **Time Tracking** (`/api/v2/volunteer/time-tracking/*`) - Clock in/out
- **Attendance Reports** (`/api/v2/staff/*/attendance`) - Attendance records and reports

### Admin Tools
- **Registration Management** (`/api/v2/registrations/*`) - Approve/reject registrations
- **Password Resets** (`/api/v2/password-resets/*`) - Password reset workflow
- **Assistant Management** (`/api/v2/assistants/*`, `/api/v2/admin/assistants/*`) - Assistant CRUD
- **Performance Monitoring** (`/api/v2/admin/performance/*`) - System health and metrics

### Communication
- **Notifications** (`/api/v2/notifications/*`) - In-app notification system
- **Profile Management** (`/api/v2/profiles/*`) - Staff and student profiles

## Authentication

Most endpoints require JWT authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## Response Format

All API responses follow a consistent format:

**Success Response:**
```json
{
  "success": true,
  "data": { ... },
  "message": "Optional success message"
}
```

**Error Response:**
```json
{
  "success": false,
  "message": "Error description",
  "errors": { ... } // Optional detailed errors
}
```

## Endpoints

### Authentication

#### POST /api/v2/auth/login
Authenticate user and receive JWT token.

**Request:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "username": "string",
      "email": "string",
      "first_name": "string", 
      "last_name": "string",
      "role": "string|null",
      "is_admin": boolean
    },
    "token": "jwt-token-string"
  },
  "message": "Login successful"
}
```

#### POST /api/v2/auth/register
Submit a new registration request (pending admin approval). This endpoint expects multipart/form-data because a profile picture upload is required.

**Content-Type:** `multipart/form-data`

**Required fields:**
- `student_id` (alias: `username`): your ID used as login
- `name` OR `first_name` + `last_name`
- `email`
- `phone`
- `degree` (e.g., `BSc` or `MSc`)
- `password` and `confirm_password` (must match; min 8 chars, 1 uppercase, 1 number, 1 special)
- `reason`: Why would you like to join the Help Desk?
- `terms` (alias: `confirm`): must be truthy (`on|true|1|yes`)
- `courses[]` (repeat field) or `courses` as a JSON array
- `availability` as a JSON array of slots
- `profile_picture` file (JPEG/PNG)
- `transcript` file (PDF)

**Optional fields/files:**
None

**Availability JSON format:**
```json
[
  { "day": 0, "start_time": "09:00:00", "end_time": "10:00:00" },
  { "day": 2, "start_time": "14:00:00", "end_time": "16:00:00" }
]
```

**PowerShell (Windows) example using curl.exe (single line):**
```powershell
curl.exe -X POST http://localhost:8080/api/v2/auth/register -F 'student_id=817000123' -F 'first_name=Jane' -F 'last_name=Doe' -F 'email=jane.doe@example.com' -F 'phone=868-555-1234' -F 'degree=BSc' -F 'password=Str0ng!Pass' -F 'confirm_password=Str0ng!Pass' -F 'reason=I enjoy helping students and solving problems.' -F 'terms=on' -F 'courses[]=COMP1601' -F 'courses[]=COMP1602' -F 'availability=[{"day":0,"start_time":"09:00:00","end_time":"10:00:00"}]' -F 'profile_picture=@C:\path\to\photo.jpg' -F 'transcript=@C:\path\to\transcript.pdf'
```

Notes:
- You may send `courses` as a JSON array instead of repeating `courses[]`.
- If you only have a single course, you can pass a single value once.
- JSON requests without `multipart/form-data` will be rejected because `profile_picture` must be uploaded as a file.

#### POST /api/v2/auth/logout
Logout current user (client should remove token).

**Authentication:** Required

#### GET /api/v2/me
Get current authenticated user's profile.

**Authentication:** Required

**Response:**
```json
{
  "success": true,
  "data": {
    "username": "string",
    "email": "string",
    "first_name": "string",
    "last_name": "string",
    "is_admin": boolean,
    "role": "string|null",
    "student_id": "string|null",
    "created_at": "ISO-8601-datetime|null"
  }
}
```

#### PUT /api/v2/me
Update current user's profile.

**Authentication:** Required

**Request:**
```json
{
  "email": "string (optional)",
  "first_name": "string (optional)",
  "last_name": "string (optional)"
}
```

### Admin Endpoints

#### GET /api/v2/admin/dashboard
Get admin dashboard data.

**Authentication:** Required (Admin only)

**Response:**
```json
{
  "success": true,
  "data": {
    "user": { "username": "string" },
    "schedules": {
      "published_count": number,
      "current_schedule": {
        "id": number,
        "start_date": "ISO-8601-date",
        "end_date": "ISO-8601-date",
        "type": "string",
        "is_published": boolean
      }
    },
    "pending_items": {
      "registrations": number,
      "requests": number,
      "total": number
    },
    "attendance": {
      "total_shifts_this_week": number,
      "attended_shifts": number,
      "missed_shifts": number,
      "attendance_rate": number
    }
  }
}
```

#### GET /api/v2/admin/stats
Get detailed administrative statistics.

**Authentication:** Required (Admin only)

### Student Endpoints

#### GET /api/v2/student/dashboard
Get student dashboard data.

**Authentication:** Required (Student only)

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "username": "string",
      "first_name": "string",
      "last_name": "string",
      "email": "string",
      "student_id": "string"
    },
    "upcoming_shifts": [
      {
        "id": number,
        "date": "ISO-8601-date",
        "start_time": "HH:MM",
        "end_time": "HH:MM",
        "schedule_id": number
      }
    ],
    "recent_time_entries": [
      {
        "id": number,
        "clock_in": "ISO-8601-datetime",
        "clock_out": "ISO-8601-datetime|null",
        "shift_id": number,
        "status": "completed|in_progress"
      }
    ],
    "stats": {
      "upcoming_shifts_count": number,
      "completed_shifts_count": number,
      "has_upcoming_shifts": boolean
    }
  }
}
```

#### GET /api/v2/student/schedule
Get student's schedule for a date range.

**Authentication:** Required (Student only)

**Query Parameters:**
- `start_date`: YYYY-MM-DD (optional, defaults to current week)
- `end_date`: YYYY-MM-DD (optional, defaults to current week)

## Testing the API

You can test the API endpoints using curl:

```bash
# Login
curl -X POST http://localhost:8080/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# Get current user (replace TOKEN with actual JWT)
curl -X GET http://localhost:8080/api/v2/me \
  -H "Authorization: Bearer TOKEN"

# Admin dashboard
curl -X GET http://localhost:8080/api/v2/admin/dashboard \
  -H "Authorization: Bearer TOKEN"
```

## Error Codes

- `400`: Bad Request - Invalid input data
- `401`: Unauthorized - Invalid or missing authentication
- `403`: Forbidden - Insufficient permissions
- `404`: Not Found - Resource not found
- `409`: Conflict - Resource already exists
- `500`: Internal Server Error - Server-side error

## Role-Based Access

- **Admin endpoints** (`/api/v2/admin/*`): Require admin role
- **Student endpoints** (`/api/v2/student/*`): Require student role  
- **Profile endpoints** (`/api/v2/me`): Require any authenticated user
- **Auth endpoints** (`/api/v2/auth/*`): Public (except logout)

## Next Steps

### For Frontend Developers
1. Visit `/api/v2/docs` in your browser for interactive API exploration
2. Use the Swagger UI to test endpoints and understand request/response formats
3. Refer to [`api_v2_conversion_status.md`](api_v2_conversion_status.md) for the complete endpoint list
4. Implement React/Next.js frontend using the standardized API responses

### For Backend Developers
1. All core functionality has been migrated to API v2
2. Follow the patterns in `App/views/api_v2/` for any new endpoints
3. Use `api_success()` and `api_error()` helpers for consistent responses
4. Always use controllers instead of direct model queries in API routes
5. See [`API_V2_DESIGN_PRINCIPLES_IMPLEMENTATION.md`](API_V2_DESIGN_PRINCIPLES_IMPLEMENTATION.md) for architectural guidance

## Migration Status

 **API v2 Migration Complete!** All core functionality has been migrated:
- Authentication & authorization
- Schedule management & configuration
- Time tracking & attendance
- User & assistant management
- Request & registration workflows
- Notifications & profiles
- Performance monitoring
- Interactive API documentation

Legacy routes remain available for the HTML web interface to maintain backward compatibility.