# API v2 Documentation

## Overview

This document describes the API v2 endpoints for the Help Desk Rostering application. These endpoints are designed to support a React/Next.js frontend and provide a clean separation between the backend API and frontend presentation.

## Base URL

All API v2 endpoints are prefixed with `/api/v2/`

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

1. Start the Flask development server: `flask run`
2. Test endpoints using curl or Postman
3. Create Next.js frontend to consume these APIs
4. Implement error handling and loading states
5. Add more endpoints as needed (courses, availability, etc.)