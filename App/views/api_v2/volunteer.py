from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required

from App.middleware import volunteer_required
from App.utils.profile_images import resolve_profile_image
from App.utils.time_utils import trinidad_now
from App.views.api_v2 import api_v2
from App.views.api_v2.utils import api_error, api_success
from App.controllers.dashboard import get_dashboard_data
from App.controllers.tracking import (
    auto_complete_time_entries,
    check_and_complete_abandoned_entry,
    clock_in,
    clock_out,
    get_shift_history,
    get_student_stats,
    get_time_distribution,
    get_today_shift,
)


def _serialize_student(student: Any) -> Optional[Dict[str, Any]]:
    if not student:
        return None

    image_url = resolve_profile_image(
        getattr(student, "profile_data", None), static_base="/static/"
    )

    return {
        "username": getattr(student, "username", None),
        "display_name": student.get_name() if hasattr(student, "get_name") else None,
        "degree": getattr(student, "degree", None),
        "profile_image_url": image_url,
    }


def _infer_shift_status(shift: Dict[str, Any]) -> str:
    if not shift:
        return "none"

    if shift.get("status"):
        return shift["status"]

    if shift.get("starts_now"):
        return "active"

    if shift.get("time"):
        return "upcoming"

    return "none"


def _format_next_shift(raw_shift: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not raw_shift:
        return {
            "status": "none",
            "date_label": None,
            "time_range": None,
            "starts_now": False,
            "time_until_label": None,
        }

    status = _infer_shift_status(raw_shift)
    return {
        "status": status,
        "date_label": raw_shift.get("date"),
        "time_range": raw_shift.get("time"),
        "starts_now": bool(raw_shift.get("starts_now")),
        "time_until_label": raw_shift.get("time_until") or None,
        "is_scheduled": status in {"active", "future", "upcoming"},
    }


def _format_schedule(raw_schedule: Dict[str, Any]) -> Dict[str, Any]:
    days = raw_schedule.get("days_of_week", [])
    time_slots = raw_schedule.get("time_slots", [])
    staff_schedule = raw_schedule.get("staff_schedule", {})

    grid: List[Dict[str, Any]] = []
    for slot in time_slots:
        assignments = []
        slot_data = staff_schedule.get(slot, {}) if isinstance(staff_schedule, dict) else {}
        for day in days:
            names = slot_data.get(day, []) if isinstance(slot_data, dict) else []
            assignments.append({
                "day": day,
                "assistants": names,
            })
        grid.append({
            "time_label": slot,
            "assignments": assignments,
        })

    return {
        "days": days,
        "time_slots": time_slots,
        "grid": grid,
    }


def _default_stats(now) -> Dict[str, Any]:
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=6)
    month_label = now.strftime("%B %Y")

    return {
        "daily": {
            "hours": 0.0,
            "hours_display": "0.0",
            "date_range": now.strftime("%d %b, %Y"),
        },
        "weekly": {
            "hours": 0.0,
            "hours_display": "0.0",
            "date_range": f"Week {now.isocalendar()[1]}, {week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
        },
        "monthly": {
            "hours": 0.0,
            "hours_display": "0.0",
            "date_range": month_label,
        },
        "semester": {
            "hours": 0.0,
            "hours_display": "0.0",
            "date_range": "Current Semester",
        },
        "absences": 0,
    }


def _format_stats(raw_stats: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    now = trinidad_now()
    if not raw_stats:
        return _default_stats(now)

    def _format_section(section: Dict[str, Any], fallback_range: str) -> Dict[str, Any]:
        hours_value = float(section.get("hours", 0.0))
        return {
            "hours": hours_value,
            "hours_display": f"{hours_value:.1f}",
            "date_range": section.get("date_range", fallback_range),
        }

    week_start = trinidad_now() - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=6)

    return {
        "daily": _format_section(
            raw_stats.get("daily", {}), now.strftime("%d %b, %Y")
        ),
        "weekly": _format_section(
            raw_stats.get("weekly", {}),
            f"Week {now.isocalendar()[1]}, {week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
        ),
        "monthly": _format_section(
            raw_stats.get("monthly", {}), now.strftime("%B %Y")
        ),
        "semester": _format_section(
            raw_stats.get("semester", {}), "Current Semester"
        ),
        "absences": int(raw_stats.get("absences", 0)),
    }


def _compute_time_tracking_actions(today_shift: Dict[str, Any]) -> Dict[str, Any]:
    status = today_shift.get("status", "none")
    starts_now = bool(today_shift.get("starts_now"))

    can_clock_in = status == "active" and not starts_now
    can_clock_out = status == "active" and starts_now

    if status in {"none", "error"}:
        clock_in_reason = "No active shift scheduled today."
    elif status == "future":
        clock_in_reason = "Shift has not started yet."
    elif status == "completed":
        clock_in_reason = "Today's shift is already completed."
    else:
        clock_in_reason = None

    if can_clock_out:
        clock_out_reason = None
    elif status == "active":
        clock_out_reason = "You must clock in before clocking out."
    else:
        clock_out_reason = clock_in_reason

    return {
        "clock_in": {
            "allowed": can_clock_in,
            "disabled_reason": None if can_clock_in else clock_in_reason,
        },
        "clock_out": {
            "allowed": can_clock_out,
            "disabled_reason": clock_out_reason,
        },
        "auto_clock_out_enabled": True,
    }


def _build_time_tracking_snapshot(username: str) -> Dict[str, Any]:
    stats = _format_stats(get_student_stats(username))
    today_shift = get_today_shift(username)
    shift_history = get_shift_history(username)
    time_distribution = get_time_distribution(username) or []

    if not time_distribution:
        day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        time_distribution = [
            {"label": day, "percentage": 0, "hours": 0.0}
            for day in day_labels
        ]

    actions = _compute_time_tracking_actions(today_shift or {})

    return {
        "today_shift": today_shift,
        "actions": actions,
        "stats": stats,
        "weekly_distribution": time_distribution,
        "recent_shifts": shift_history,
        "metadata": {
            "generated_at": trinidad_now().isoformat(),
            "timezone": "UTC-04:00",
        },
    }


@api_v2.route("/volunteer/dashboard", methods=["GET"])
@jwt_required()
@volunteer_required
def volunteer_dashboard_summary():
    """Return dashboard data for the authenticated volunteer."""
    try:
        username = get_jwt_identity()
        check_and_complete_abandoned_entry(username)

        dashboard_data = get_dashboard_data(username)
        if not dashboard_data:
            return api_error("Unable to load dashboard data", status_code=404)

        student = _serialize_student(dashboard_data.get("student"))
        next_shift = _format_next_shift(dashboard_data.get("next_shift"))

        upcoming_shifts = [
            {
                "date_label": shift.get("date"),
                "time_range": shift.get("time"),
            }
            for shift in dashboard_data.get("my_shifts", [])
        ]

        schedule_payload = _format_schedule(dashboard_data.get("full_schedule", {}))

        return api_success(
            data={
                "student": student,
                "next_shift": next_shift,
                "upcoming_shifts": upcoming_shifts,
                "schedule": schedule_payload,
                "metadata": {
                    "generated_at": trinidad_now().isoformat(),
                },
            }
        )
    except Exception as exc:  # pragma: no cover
        return api_error(f"Failed to load dashboard data: {exc}", status_code=500)


@api_v2.route("/volunteer/time-tracking", methods=["GET"])
@jwt_required()
@volunteer_required
def volunteer_time_tracking_overview():
    """Return time tracking metrics and today's shift state for the volunteer."""
    try:
        username = get_jwt_identity()

        # Ensure any lingering sessions are reconciled before calculating stats
        auto_complete_time_entries()

        snapshot = _build_time_tracking_snapshot(username)

        return api_success(data=snapshot)
    except Exception as exc:  # pragma: no cover
        return api_error(f"Failed to load time tracking data: {exc}", status_code=500)


@api_v2.route("/volunteer/time-tracking/clock-in", methods=["POST"])
@jwt_required()
@volunteer_required
def volunteer_clock_in():
    """Clock the authenticated volunteer into their current shift."""
    username = get_jwt_identity()

    try:
        auto_complete_time_entries()

        request_data = request.get_json(silent=True) or {}
        shift_id = request_data.get("shift_id")

        today_shift = get_today_shift(username)

        if not today_shift or today_shift.get("status") != "active":
            return api_error("No active shift found for clocking in", status_code=400)

        if today_shift.get("starts_now"):
            return api_error("You are already clocked in for this shift", status_code=400)

        if not shift_id:
            shift_id = today_shift.get("shift_id")

        if not shift_id:
            return api_error("Unable to identify the active shift", status_code=400)

        result = clock_in(username, shift_id)

        if not result.get("success"):
            return api_error(result.get("message", "Clock-in failed"), status_code=400)

        snapshot = _build_time_tracking_snapshot(username)

        return api_success(
            data={
                "time_entry": {
                    "id": result.get("time_entry_id"),
                    "message": result.get("message"),
                },
                "snapshot": snapshot,
            },
            message=result.get("message", "Clocked in successfully"),
        )
    except Exception as exc:  # pragma: no cover
        return api_error(f"Failed to clock in: {exc}", status_code=500)


@api_v2.route("/volunteer/time-tracking/clock-out", methods=["POST"])
@jwt_required()
@volunteer_required
def volunteer_clock_out():
    """Clock the authenticated volunteer out of their active shift."""
    username = get_jwt_identity()

    try:
        auto_complete_time_entries()

        today_shift = get_today_shift(username)

        if not today_shift or not today_shift.get("starts_now"):
            return api_error("You are not currently clocked in", status_code=400)

        result = clock_out(username)

        if not result.get("success"):
            return api_error(result.get("message", "Clock-out failed"), status_code=400)

        snapshot = _build_time_tracking_snapshot(username)

        return api_success(
            data={
                "time_entry": {
                    "id": result.get("time_entry_id"),
                    "hours_worked": result.get("hours_worked"),
                    "message": result.get("message"),
                },
                "snapshot": snapshot,
            },
            message=result.get("message", "Clocked out successfully"),
        )
    except Exception as exc:  # pragma: no cover
        return api_error(f"Failed to clock out: {exc}", status_code=500)
