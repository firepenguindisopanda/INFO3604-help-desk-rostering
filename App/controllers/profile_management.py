from __future__ import annotations

import json
from datetime import time as dt_time
from typing import Any, Dict, List, Optional, Tuple

from flask import url_for

from App.database import db
from App.models import (
    Availability,
    Course,
    CourseCapability,
    HelpDeskAssistant,
    LabAssistant,
    Student,
    User,
)
from App.utils.profile_images import resolve_profile_image

ProfileContext = Dict[str, Any]


def _resolve_static_base() -> Optional[str]:
    try:
        return url_for('static', filename='')
    except RuntimeError:
        return None


def _build_profile_image(profile_data: Any) -> str:
    static_base = _resolve_static_base()
    return resolve_profile_image(profile_data, static_base=static_base)


def _parse_profile_data(raw: Any) -> Dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return {}
    return {}


def get_admin_profile_context(admin_user: User) -> ProfileContext:
    admin_profile = {
        'name': admin_user.username,
        'username': admin_user.username,
        'email': f"{admin_user.username}@admin.uwi.edu",
        'role': admin_user.role,
        'profile_image_url': _build_profile_image(getattr(admin_user, 'profile_data', None)),
    }

    assistant_usernames: List[str] = []
    if admin_user.role == 'helpdesk':
        assistant_usernames = [assistant.username for assistant in HelpDeskAssistant.query.filter_by(active=True).all()]
    elif admin_user.role == 'lab':
        assistant_usernames = [assistant.username for assistant in LabAssistant.query.filter_by(active=True).all()]

    formatted_students: List[Dict[str, Any]] = []
    for username in assistant_usernames:
        student = Student.query.filter_by(username=username).first()
        if not student:
            continue

        profile_data = _parse_profile_data(getattr(student, 'profile_data', None))
        formatted_students.append({
            'username': student.username,
            'name': student.name or student.username,
            'image_filename': profile_data.get('image_filename', ''),
            'profile_image_url': _build_profile_image(getattr(student, 'profile_data', None)),
        })

    return {
        'admin_profile': admin_profile,
        'students': formatted_students,
    }


def get_staff_profile_details(username: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    user = User.query.get(username)
    if not user:
        return None, 'User not found'

    student = Student.query.get(username)
    if not student:
        return None, 'Student profile not found'

    assistant = HelpDeskAssistant.query.get(username)
    assistant_defaults = {
        'active': assistant.active if assistant else True,
        'rate': assistant.rate if assistant else 20.0,
        'hours_worked': assistant.hours_worked if assistant else 0,
        'hours_minimum': assistant.hours_minimum if assistant else 4,
    }

    course_capabilities = CourseCapability.query.filter_by(assistant_username=username).all()
    availabilities = Availability.query.filter_by(username=username).all()
    profile_data = _parse_profile_data(getattr(student, 'profile_data', None))

    profile_payload = {
        'username': username,
        'name': student.name or username,
        'degree': student.degree,
        'active': assistant_defaults['active'],
        'rate': assistant_defaults['rate'],
        'hours_worked': assistant_defaults['hours_worked'],
        'hours_minimum': assistant_defaults['hours_minimum'],
        'courses': [cap.course_code for cap in course_capabilities],
        'availabilities': [availability.get_json() for availability in availabilities],
        'email': profile_data.get('email', f"{username}@my.uwi.edu"),
        'phone': profile_data.get('phone', ''),
        'image_filename': profile_data.get('image_filename', ''),
        'profile_image_url': _build_profile_image(getattr(student, 'profile_data', None)),
    }

    return profile_payload, None


def _ensure_assistant(username: str) -> HelpDeskAssistant:
    assistant = HelpDeskAssistant.query.get(username)
    if assistant:
        return assistant
    assistant = HelpDeskAssistant(username)
    db.session.add(assistant)
    db.session.flush()
    return assistant


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == 'true'
    return bool(value)


def update_student_profile(username: str, data: Dict[str, Any]) -> Tuple[bool, str, int]:
    student = Student.query.get(username)
    if not student:
        return False, f'Student with username {username} not found', 404

    assistant = _ensure_assistant(username)

    if 'name' in data:
        student.name = data['name']

    if 'degree' in data:
        student.degree = data['degree']

    if 'rate' in data:
        try:
            assistant.rate = float(data['rate'])
        except (TypeError, ValueError):
            return False, 'Rate must be a valid number', 400

    if 'hours_minimum' in data:
        try:
            assistant.hours_minimum = int(data['hours_minimum'])
        except (TypeError, ValueError):
            return False, 'Minimum hours must be a valid integer', 400

    if 'active' in data:
        assistant.active = _coerce_bool(data['active'])

    try:
        db.session.add(student)
        db.session.add(assistant)
        db.session.commit()
    except Exception as exc:  # pragma: no cover - defensive rollback
        db.session.rollback()
        return False, f'An error occurred while updating the profile: {str(exc)}', 500

    return True, 'Student profile updated successfully', 200


def _parse_time_component(value: Any) -> Optional[dt_time]:
    if isinstance(value, dt_time):
        return value
    if not value:
        return None
    if isinstance(value, (int, float)):
        hour = int(value)
        return dt_time(hour=hour)
    if isinstance(value, str):
        pieces = value.split(':')
        try:
            hour = int(pieces[0])
            minute = int(pieces[1]) if len(pieces) > 1 else 0
            second = int(pieces[2]) if len(pieces) > 2 else 0
            return dt_time(hour=hour, minute=minute, second=second)
        except (TypeError, ValueError):
            return None
    return None


def admin_update_staff_profile(username: str, data: Dict[str, Any]) -> Tuple[bool, str, int]:
    student = Student.query.get(username)
    if not student:
        return False, f'Student with username {username} not found', 404

    assistant = _ensure_assistant(username)

    if 'name' in data:
        student.name = data['name']

    if 'degree' in data:
        student.degree = data['degree']

    if 'rate' in data:
        try:
            assistant.rate = float(data['rate'])
        except (TypeError, ValueError):
            return False, 'Rate must be a valid number', 400

    if 'hours_minimum' in data:
        try:
            assistant.hours_minimum = int(data['hours_minimum'])
        except (TypeError, ValueError):
            return False, 'Minimum hours must be a valid integer', 400

    if 'active' in data:
        assistant.active = _coerce_bool(data['active'])

    profile_data = _parse_profile_data(getattr(student, 'profile_data', None))
    profile_modified = False

    if 'email' in data:
        profile_data['email'] = data['email']
        profile_modified = True
    if 'phone' in data:
        profile_data['phone'] = data['phone']
        profile_modified = True

    if profile_modified:
        student.profile_data = json.dumps(profile_data)

    if 'courses' in data:
        CourseCapability.query.filter_by(assistant_username=username).delete()
        for course_code in data['courses']:
            if not course_code:
                continue
            course = Course.query.get(course_code)
            if not course:
                course = Course(course_code, f"Course {course_code}")
                db.session.add(course)
            capability = CourseCapability(username, course_code)
            db.session.add(capability)

    if 'availabilities' in data:
        Availability.query.filter_by(username=username).delete()
        for slot in data['availabilities']:
            day_raw = slot.get('day')
            start_time = _parse_time_component(slot.get('start_time'))
            end_time = _parse_time_component(slot.get('end_time'))
            try:
                day_idx = int(day_raw)
            except (TypeError, ValueError):
                continue
            if start_time is None or end_time is None:
                continue
            if day_idx < 0 or day_idx > 6:
                continue
            availability = Availability(username, day_idx, start_time, end_time)
            db.session.add(availability)

    try:
        db.session.add(student)
        db.session.add(assistant)
        db.session.commit()
    except Exception as exc:  # pragma: no cover - defensive rollback
        db.session.rollback()
        return False, f'An error occurred while updating the profile: {str(exc)}', 500

    return True, 'Profile updated successfully', 200
