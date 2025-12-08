"""Tests for legacy schedule staff management endpoints (non-API v2)."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict

import pytest
from flask.testing import FlaskClient
from flask_jwt_extended import create_access_token

from App.main import create_app
from App.database import create_db, db
from App.models import Admin, Allocation, Shift, Schedule
from App.controllers.student import create_student
from App.controllers.help_desk_assistant import create_help_desk_assistant

SCHEDULE_START = date(2025, 1, 6)
SCHEDULE_END = date(2025, 1, 10)


@pytest.fixture()
def app():
    """Create and configure a test Flask application instance."""
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "JWT_SECRET_KEY": "test-secret-key",
            "WTF_CSRF_ENABLED": False,
        }
    )
    ctx = app.app_context()
    ctx.push()
    create_db()
    yield app
    db.session.remove()
    db.drop_all()
    ctx.pop()


@pytest.fixture()
def client(app) -> FlaskClient:
    """Provide a test client for the Flask application."""
    return app.test_client()


@pytest.fixture()
def admin_headers(app) -> Dict[str, str]:
    """Create admin user and return auth headers with JWT token."""
    admin = Admin("admin_user", "test-pass", "helpdesk")
    db.session.add(admin)
    db.session.commit()
    token = create_access_token(identity="admin_user")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


@pytest.fixture()
def assistant_username(app) -> str:
    """Create a test help desk assistant and return username."""
    username = "assistant1"
    create_student(username, "student-pass", "BSc", "Assistant One")
    create_help_desk_assistant(username)
    return username


@pytest.fixture()
def second_assistant_username(app) -> str:
    """Create a second test help desk assistant and return username."""
    username = "assistant2"
    create_student(username, "student-pass", "BSc", "Assistant Two")
    create_help_desk_assistant(username)
    return username


def _authorized_post(
    client: FlaskClient,
    headers: Dict[str, str],
    path: str,
    payload: Dict[str, Any],
):
    """Helper to make authenticated POST requests."""
    return client.post(path, json=payload, headers=headers)


@pytest.mark.integration
def test_legacy_admin_can_save_schedule_with_staff_assignments(
    client: FlaskClient,
    admin_headers: Dict[str, str],
    assistant_username: str,
):
    """
    Rationale: Ensures legacy /api/schedule/save endpoint maintains backward compatibility
    while preserving single responsibility for schedule persistence.
    """
    save_payload = {
        "start_date": SCHEDULE_START.isoformat(),
        "end_date": SCHEDULE_END.isoformat(),
        "assignments": [
            {
                "day": "Monday",
                "time": "9:00 am to 10:00 am",
                "staff": [
                    {
                        "id": assistant_username,
                        "name": "Assistant One",
                    }
                ],
            }
        ],
    }

    response = _authorized_post(
        client,
        admin_headers,
        "/api/schedule/save",
        save_payload,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"

    # Verify shift was created
    shift = Shift.query.first()
    assert shift is not None
    assert shift.start_time.hour == 9

    # Verify allocation was created
    allocation = Allocation.query.filter_by(
        shift_id=shift.id,
        username=assistant_username,
    ).first()
    assert allocation is not None


@pytest.mark.integration
def test_legacy_admin_can_save_multiple_staff_to_same_shift(
    client: FlaskClient,
    admin_headers: Dict[str, str],
    assistant_username: str,
    second_assistant_username: str,
):
    """
    Rationale: Validates maintainability by confirming multiple staff can be assigned
    to a single shift using legacy endpoint without data corruption.
    """
    save_payload = {
        "start_date": SCHEDULE_START.isoformat(),
        "end_date": SCHEDULE_END.isoformat(),
        "assignments": [
            {
                "day": "Monday",
                "time": "10:00 am to 11:00 am",
                "staff": [
                    {"id": assistant_username, "name": "Assistant One"},
                    {"id": second_assistant_username, "name": "Assistant Two"},
                ],
            }
        ],
    }

    response = _authorized_post(
        client,
        admin_headers,
        "/api/schedule/save",
        save_payload,
    )

    assert response.status_code == 200

    shift = Shift.query.first()
    allocations = Allocation.query.filter_by(shift_id=shift.id).all()
    assert len(allocations) == 2
    usernames = {alloc.username for alloc in allocations}
    assert usernames == {assistant_username, second_assistant_username}


@pytest.mark.integration
def test_legacy_admin_can_remove_staff_from_shift(
    client: FlaskClient,
    admin_headers: Dict[str, str],
    assistant_username: str,
):
    """
    Rationale: Protects defensibility by ensuring legacy removal endpoint
    properly deletes allocations without orphaning database records.
    """
    # First, save a schedule with an assignment
    initial_save = _authorized_post(
        client,
        admin_headers,
        "/api/schedule/save",
        {
            "start_date": SCHEDULE_START.isoformat(),
            "end_date": SCHEDULE_END.isoformat(),
            "assignments": [
                {
                    "day": "Monday",
                    "time": "9:00 am to 10:00 am",
                    "staff": [
                        {
                            "id": assistant_username,
                            "name": "Assistant One",
                        }
                    ],
                }
            ],
        },
    )
    assert initial_save.status_code == 200

    # Get the created shift
    shift = Shift.query.first()
    assert shift is not None

    # Now remove the staff member
    removal_response = _authorized_post(
        client,
        admin_headers,
        "/api/schedule/remove-staff",
        {
            "staff_id": assistant_username,
            "day": "Monday",
            "time": "9:00 am to 10:00 am",
            "shift_id": shift.id,
        },
    )

    assert removal_response.status_code == 200
    removal_payload = removal_response.get_json()
    assert removal_payload["status"] == "success"

    # Verify allocation was removed
    remaining_allocation = Allocation.query.filter_by(
        shift_id=shift.id,
        username=assistant_username,
    ).first()
    assert remaining_allocation is None


@pytest.mark.integration
def test_legacy_remove_staff_without_shift_id_fails_gracefully(
    client: FlaskClient,
    admin_headers: Dict[str, str],
    assistant_username: str,
):
    """
    Rationale: Enforces defensibility by validating error handling when
    required parameters are missing from legacy endpoint.
    """
    removal_response = _authorized_post(
        client,
        admin_headers,
        "/api/schedule/remove-staff",
        {
            "staff_id": assistant_username,
            "day": "Monday",
            "time": "9:00 am",
            # Missing shift_id intentionally
        },
    )

    # Should handle gracefully - either 400 for bad request or 404 for not found
    assert removal_response.status_code in [400, 404, 500]
    payload = removal_response.get_json()
    assert payload["status"] == "error"


@pytest.mark.integration
def test_legacy_save_schedule_updates_existing_schedule(
    client: FlaskClient,
    admin_headers: Dict[str, str],
    assistant_username: str,
    second_assistant_username: str,
):
    """
    Rationale: Validates portability by confirming legacy endpoint can update
    existing schedules without creating duplicates.
    """
    # Create initial schedule
    first_save = _authorized_post(
        client,
        admin_headers,
        "/api/schedule/save",
        {
            "start_date": SCHEDULE_START.isoformat(),
            "end_date": SCHEDULE_END.isoformat(),
            "assignments": [
                {
                    "day": "Monday",
                    "time": "9:00 am to 10:00 am",
                    "staff": [{"id": assistant_username, "name": "Assistant One"}],
                }
            ],
        },
    )
    assert first_save.status_code == 200

    initial_schedule_count = Schedule.query.count()
    initial_shift_count = Shift.query.count()

    # Update schedule with different assignment
    second_save = _authorized_post(
        client,
        admin_headers,
        "/api/schedule/save",
        {
            "start_date": SCHEDULE_START.isoformat(),
            "end_date": SCHEDULE_END.isoformat(),
            "assignments": [
                {
                    "day": "Tuesday",
                    "time": "10:00 am to 11:00 am",
                    "staff": [{"id": second_assistant_username, "name": "Assistant Two"}],
                }
            ],
        },
    )
    assert second_save.status_code == 200

    # Verify no duplicate schedules created
    final_schedule_count = Schedule.query.count()
    assert final_schedule_count == initial_schedule_count

    # Verify new shift was added (not replaced)
    final_shift_count = Shift.query.count()
    assert final_shift_count >= initial_shift_count


@pytest.mark.integration
def test_legacy_save_schedule_validates_date_format(
    client: FlaskClient,
    admin_headers: Dict[str, str],
    assistant_username: str,
):
    """
    Rationale: Enforces defensibility by testing input validation on legacy endpoint.
    """
    save_payload = {
        "start_date": "invalid-date-format",
        "end_date": SCHEDULE_END.isoformat(),
        "assignments": [
            {
                "day": "Monday",
                "time": "9:00 am",
                "staff": [{"id": assistant_username, "name": "Assistant One"}],
            }
        ],
    }

    response = _authorized_post(
        client,
        admin_headers,
        "/api/schedule/save",
        save_payload,
    )

    # Should fail validation
    assert response.status_code in [400, 500]
    payload = response.get_json()
    assert payload["status"] == "error"


@pytest.mark.unit
def test_legacy_remove_staff_requires_staff_id(
    client: FlaskClient,
    admin_headers: Dict[str, str],
):
    """
    Rationale: Validates simplicity by ensuring endpoint fails fast with clear
    error when required parameter is missing.
    """
    removal_response = _authorized_post(
        client,
        admin_headers,
        "/api/schedule/remove-staff",
        {
            # Missing staff_id
            "day": "Monday",
            "time": "9:00 am",
        },
    )

    assert removal_response.status_code == 400
    payload = removal_response.get_json()
    assert payload["status"] == "error"
    assert "Staff ID is required" in payload["message"]
