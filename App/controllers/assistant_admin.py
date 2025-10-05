from typing import Dict, Any, Tuple
from sqlalchemy.exc import SQLAlchemyError
from App.database import db
from App.models import Student, HelpDeskAssistant, LabAssistant, TimeEntry, User


def _is_assistant(username: str) -> bool:
    """Return True if the username corresponds to any assistant type."""
    if HelpDeskAssistant.query.get(username):
        return True
    if LabAssistant.query.get(username):
        return True
    return False


def delete_assistant_fully(username: str) -> Tuple[bool, Dict[str, Any]]:
    """Delete an assistant (student) and cascade related data.

    Guards:
      - Must exist as a student
      - Must NOT be an admin user
      - Must be an assistant (helpdesk or lab)
      - Cannot have active time entries (status = 'active')

    Returns:
      (success, payload) where payload contains message or error details.
    """
    try:
        student: Student | None = Student.query.get(username)
        if not student:
            return False, {"message": "Student not found", "code": 404}

        user: User | None = User.query.get(username)
        if user and user.is_admin():
            return False, {"message": "Cannot delete an admin user", "code": 400}

        if not _is_assistant(username):
            return False, {"message": "User is not an assistant", "code": 400}

        # Active time entry guard
        active_entry = TimeEntry.query.filter_by(username=username, status='active').first()
        if active_entry:
            return False, {"message": "Assistant has an active time entry. Clock out before deletion.", "code": 409}

        # Collect counts before delete for reporting
        counts = {
            "time_entries": TimeEntry.query.filter_by(username=username).count(),
            # Additional related tables rely on cascade; counts for debug only
        }

        db.session.delete(student)  # Cascades through FKs & relationships
        db.session.commit()
        return True, {"message": "Assistant deleted", "username": username, "removed": counts}
    except SQLAlchemyError as e:
        db.session.rollback()
        return False, {"message": f"Database error: {str(e)}", "code": 500}
    except Exception as e:
        db.session.rollback()
        return False, {"message": f"Unexpected error: {str(e)}", "code": 500}
