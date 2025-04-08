from App.database import db
from datetime import datetime

class PasswordResetRequest(db.Model):
    __tablename__ = 'password_reset_requests'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False)  # Removed foreign key for now
    reason = db.Column(db.String(500))
    status = db.Column(db.String(30), default="PENDING")  # PENDING, COMPLETED, REJECTED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    processed_by = db.Column(db.String(120))  # Removed foreign key for now
    rejection_reason = db.Column(db.String(500))

    def __init__(self, username, reason, status="PENDING", created_at=None):
        self.username = username
        self.reason = reason
        self.status = status
        if created_at:
            self.created_at = created_at