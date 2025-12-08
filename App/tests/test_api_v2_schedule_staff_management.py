"""Tests for admin schedule staff management endpoints."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict

import pytest
from flask.testing import FlaskClient
from flask_jwt_extended import create_access_token

from App.main import create_app
from App.database import create_db, db
from App.models import Admin, Allocation, Shift
from App.controllers.student import create_student
from App.controllers.help_desk_assistant import create_help_desk_assistant

SCHEDULE_START = date(2025, 1, 6)
SCHEDULE_END = date(2025, 1, 10)


@pytest.fixture()
def app():
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
    return app.test_client()


@pytest.fixture()
def admin_headers(app) -> Dict[str, str]:
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
    username = "assistant1"
    create_student(username, "student-pass", "BSc", "Assistant One")
    create_help_desk_assistant(username)
    return username


def _authorized_post(
    client: FlaskClient,
    headers: Dict[str, str],
    path: str,
    payload: Dict[str, Any],
):
    return client.post(path, json=payload, headers=headers)


@pytest.mark.integration
def test_admin_can_assign_staff_to_shift(
    client: FlaskClient,
    admin_headers: Dict[str, str],
    assistant_username: str,
):
    """Rationale: protects maintainability by exercising the single API used to persist schedule assignments."""
    save_payload = {
        "start_date": SCHEDULE_START.isoformat(),
        "end_date": SCHEDULE_END.isoformat(),
        "schedule_type": "helpdesk",
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
        "/api/v2/admin/schedule/save",
        save_payload,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"]
    assert payload["data"]["assignments_processed"] == 1

    created_shift = Shift.query.one()
    assert created_shift.start_time.hour == 9
    allocation = Allocation.query.filter_by(
        shift_id=created_shift.id,
        username=assistant_username,
    ).one_or_none()
    assert allocation is not None


@pytest.mark.integration
def test_admin_can_remove_staff_from_shift(
    client: FlaskClient,
    admin_headers: Dict[str, str],
    assistant_username: str,
):
    """Rationale: enforces defensibility by verifying stale allocations are purged via the removal endpoint."""
    initial_save = _authorized_post(
        client,
        admin_headers,
        "/api/v2/admin/schedule/save",
        {
            "start_date": SCHEDULE_START.isoformat(),
            "end_date": SCHEDULE_END.isoformat(),
            "schedule_type": "helpdesk",
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

    shift = Shift.query.one()
    removal_response = _authorized_post(
        client,
        admin_headers,
        "/api/v2/admin/schedule/staff/remove",
        {
            "staff_id": assistant_username,
            "shift_id": shift.id,
        },
    )

    assert removal_response.status_code == 200
    removal_payload = removal_response.get_json()
    assert removal_payload["success"]
    remaining_allocation = Allocation.query.filter_by(
        shift_id=shift.id,
        username=assistant_username,
    ).first()
    assert remaining_allocation is None
