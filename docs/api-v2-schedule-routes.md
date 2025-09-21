# API v2 Schedule Routes Documentation

## Overview

Professional Flask API v2 routes for schedule management, designed with enterprise-grade practices including comprehensive validation, error handling, and standardized response formats.

## Base URL
```
/api/v2/admin/schedule/*
```

## Authentication
All routes require:
- `@jwt_required()` - Valid JWT token
- `@admin_required` - Admin role privileges

## Response Format

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Optional success message"
}
```

### Error Response
```json
{
  "success": false,
  "message": "Error description",
  "errors": { ... }  // Optional detailed errors
}
```

## Schedule Management Endpoints

### 1. Generate Schedule
**POST** `/api/v2/admin/schedule/generate`

Generate a new schedule for the current admin's domain (helpdesk/lab).

**Request Body:**
```json
{
  "start_date": "2025-09-22",
  "end_date": "2025-09-26"
}
```

**Response (201):**
```json
{
  "success": true,
  "data": {
    "schedule_id": 1,
    "schedule_type": "helpdesk",
    "start_date": "2025-09-22",
    "end_date": "2025-09-26",
    "shifts_generated": 45,
    "generation_time": "2.3s",
    "optimization_status": "OPTIMAL"
  },
  "message": "Schedule generated successfully for helpdesk domain"
}
```

**Validation:**
- Date format: YYYY-MM-DD
- Start date ≤ End date
- End date ≤ 1 year in future
- Admin role determines schedule type

---

### 2. Get Current Schedule
**GET** `/api/v2/admin/schedule/current`

Retrieve the current active schedule for the admin's domain.

**Response (200):**
```json
{
  "success": true,
  "data": {
    "schedule": {
      "id": 1,
      "type": "helpdesk",
      "start_date": "2025-09-22",
      "end_date": "2025-09-26",
      "days": [
        {
          "day": "Monday",
          "shifts": [
            {
              "shift_id": 101,
              "time": "9:00 am",
              "assistants": [
                {"id": "staff001", "name": "John Doe"}
              ]
            }
          ]
        }
      ]
    },
    "schedule_type": "helpdesk"
  },
  "message": "Current schedule retrieved successfully"
}
```

---

### 3. Get Schedule Details
**GET** `/api/v2/admin/schedule/details?id=1`

Get detailed schedule information by ID.

**Query Parameters:**
- `id` (integer, required): Schedule ID

**Response (200):**
```json
{
  "success": true,
  "data": {
    "schedule": {
      "id": 1,
      "type": "helpdesk",
      "is_published": true,
      "days": [...],
      "statistics": {
        "total_shifts": 45,
        "assigned_shifts": 42,
        "coverage_percentage": 93.3
      }
    }
  },
  "message": "Schedule details retrieved successfully"
}
```

---

### 4. Save Schedule
**POST** `/api/v2/admin/schedule/save`

Save schedule changes and staff assignments.

**Request Body:**
```json
{
  "start_date": "2025-09-22",
  "end_date": "2025-09-26",
  "schedule_type": "helpdesk",
  "assignments": [
    {
      "day": "Monday",
      "time": "9:00 am",
      "cell_id": "cell-0-0",
      "staff": [
        {"id": "staff001", "name": "John Doe"},
        {"id": "staff002", "name": "Jane Smith"}
      ]
    }
  ]
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "schedule_id": 1,
    "schedule_type": "helpdesk",
    "assignments_processed": 45,
    "start_date": "2025-09-22",
    "end_date": "2025-09-26",
    "errors": null
  },
  "message": "Schedule saved successfully"
}
```

---

### 5. Clear Schedule
**POST** `/api/v2/admin/schedule/clear`

Clear an existing schedule and all its assignments.

**Request Body:**
```json
{
  "schedule_type": "helpdesk",
  "schedule_id": 1
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "schedule_id": 1,
    "schedule_type": "helpdesk",
    "cleared_at": "2025-09-20T14:30:00Z"
  },
  "message": "Schedule cleared successfully for helpdesk domain"
}
```

---

### 6. Publish Schedule
**POST** `/api/v2/admin/schedule/{schedule_id}/publish`

Publish a schedule to make it active and notify staff.

**Path Parameters:**
- `schedule_id` (integer): Schedule ID to publish

**Response (200):**
```json
{
  "success": true,
  "data": {
    "schedule_id": 1,
    "published_at": "2025-09-20T14:30:00Z",
    "notifications_sent": 25
  },
  "message": "Schedule published successfully"
}
```

## Staff Management Endpoints

### 7. Get Available Staff
**GET** `/api/v2/admin/schedule/staff/available?day=Monday&time=9:00 am`

Get staff available for a specific day and time.

**Query Parameters:**
- `day` (string, required): Day of week (e.g., "Monday")
- `time` (string, required): Time slot (e.g., "9:00 am")

**Response (200):**
```json
{
  "success": true,
  "data": {
    "staff": [
      {"id": "staff001", "name": "John Doe", "type": "student"},
      {"id": "staff002", "name": "Jane Smith", "type": "student"}
    ],
    "day": "Monday",
    "time": "9:00 am",
    "count": 2
  },
  "message": "Retrieved 2 available staff for Monday at 9:00 am"
}
```

---

### 8. Check Staff Availability
**GET** `/api/v2/admin/schedule/staff/check-availability?staff_id=staff001&day=Monday&time=9:00 am`

Check if a specific staff member is available at a given time.

**Query Parameters:**
- `staff_id` (string, required): Staff member ID
- `day` (string, required): Day of week
- `time` (string, required): Time slot

**Response (200):**
```json
{
  "success": true,
  "data": {
    "staff_id": "staff001",
    "day": "Monday",
    "time": "9:00 am",
    "is_available": true
  },
  "message": "Availability check completed"
}
```

---

### 9. Batch Check Availability
**POST** `/api/v2/admin/schedule/staff/check-availability/batch`

Check availability for multiple staff/time combinations in a single request.

**Request Body:**
```json
{
  "queries": [
    {
      "staff_id": "staff001",
      "day": "Monday",
      "time": "9:00 am"
    },
    {
      "staff_id": "staff002",
      "day": "Monday",
      "time": "10:00 am"
    }
  ]
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "staff_id": "staff001",
        "day": "Monday",
        "time": "9:00 am",
        "is_available": true
      },
      {
        "staff_id": "staff002",
        "day": "Monday", 
        "time": "10:00 am",
        "is_available": false
      }
    ],
    "total_queries": 2,
    "processed": 2
  },
  "message": "Batch availability check completed for 2 queries"
}
```

**Limits:**
- Maximum 500 queries per batch

---

### 10. Remove Staff from Shift
**POST** `/api/v2/admin/schedule/staff/remove`

Remove a staff member from a specific shift.

**Request Body:**
```json
{
  "staff_id": "staff001",
  "day": "Monday",
  "time": "9:00 am",
  "shift_id": 101
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "staff_id": "staff001",
    "day": "Monday",
    "time": "9:00 am",
    "shift_id": 101,
    "removed_at": "2025-09-20T14:30:00Z"
  },
  "message": "Staff member removed from shift successfully"
}
```

## Export & Reporting Endpoints

### 11. Export Schedule PDF
**GET** `/api/v2/admin/schedule/export/pdf?format=standard`

Export current schedule as PDF.

**Query Parameters:**
- `format` (string, optional): PDF format type (default: "standard")

**Response:** PDF file download

**Headers:**
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="helpdesk_schedule_20250920.pdf"
```

---

### 12. Get Schedule Summary
**GET** `/api/v2/admin/schedule/summary`

Get summary statistics for the current schedule.

**Response (200):**
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_shifts": 45,
      "assigned_shifts": 42,
      "unassigned_shifts": 3,
      "total_staff_assignments": 89,
      "coverage_percentage": 93.33,
      "schedule_type": "helpdesk",
      "schedule_id": 1,
      "start_date": "2025-09-22",
      "end_date": "2025-09-26",
      "is_published": true
    },
    "schedule_type": "helpdesk",
    "generated_at": "2025-09-20T14:30:00Z"
  },
  "message": "Schedule summary retrieved successfully"
}
```

## Error Codes

| Status | Description | Example |
|--------|-------------|---------|
| 400 | Bad Request | Invalid date format, missing required fields |
| 401 | Unauthorized | Invalid or missing JWT token |
| 403 | Forbidden | Non-admin user accessing admin endpoints |
| 404 | Not Found | Schedule not found, no current schedule |
| 500 | Internal Server Error | Database errors, generation failures |

## Usage Examples

### cURL Examples

**Generate Schedule:**
```bash
curl -X POST http://localhost:8080/api/v2/admin/schedule/generate \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2025-09-22","end_date":"2025-09-26"}'
```

**Get Available Staff:**
```bash
curl -X GET "http://localhost:8080/api/v2/admin/schedule/staff/available?day=Monday&time=9:00%20am" \
  -H "Authorization: Bearer <JWT>"
```

**Save Schedule:**
```bash
curl -X POST http://localhost:8080/api/v2/admin/schedule/save \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d @schedule_data.json
```

### JavaScript/Fetch Examples

**Generate Schedule:**
```javascript
const response = await fetch('/api/v2/admin/schedule/generate', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    start_date: '2025-09-22',
    end_date: '2025-09-26'
  })
});

const result = await response.json();
if (result.success) {
  console.log('Schedule generated:', result.data);
} else {
  console.error('Error:', result.message);
}
```

**Batch Check Availability:**
```javascript
const queries = [
  { staff_id: 'staff001', day: 'Monday', time: '9:00 am' },
  { staff_id: 'staff002', day: 'Monday', time: '10:00 am' }
];

const response = await fetch('/api/v2/admin/schedule/staff/check-availability/batch', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ queries })
});

const result = await response.json();
result.data.results.forEach(availability => {
  console.log(`${availability.staff_id}: ${availability.is_available ? 'Available' : 'Not Available'}`);
});
```

## Implementation Notes

### Professional Patterns Applied

1. **Comprehensive Validation**: All inputs validated with detailed error messages
2. **Standardized Responses**: Consistent JSON format across all endpoints
3. **Error Handling**: Graceful error handling with rollback on failures
4. **Security**: JWT authentication and role-based authorization
5. **Performance**: Batch operations for efficiency, caching strategies
6. **Logging**: Comprehensive logging for debugging and monitoring
7. **Documentation**: Extensive inline documentation and type hints

### Architecture Decisions

1. **Controller Layer Separation**: Business logic in controllers, routes handle HTTP concerns
2. **Constants**: Centralized constants for maintainable code
3. **Helper Functions**: Complex functions broken down for cognitive simplicity
4. **Timezone Handling**: Proper UTC timestamp handling
5. **Database Transactions**: Proper transaction management with rollback

### Next.js Integration

These API routes are designed to work seamlessly with Next.js applications:

1. **RESTful Design**: Standard HTTP methods and status codes
2. **JSON First**: All data exchange in JSON format
3. **CORS Ready**: Can be configured for cross-origin requests
4. **TypeScript Friendly**: Predictable response structures for type definitions
5. **Modern Standards**: Follows modern web API best practices

This professional API implementation provides a solid foundation for the Next.js schedule management interface while maintaining enterprise-grade reliability and maintainability.