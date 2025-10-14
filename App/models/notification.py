from datetime import datetime
from App.database import db
from App.utils.time_utils import trinidad_now, convert_to_trinidad_time

class Notification(db.Model):
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), db.ForeignKey('users.username', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, index=True)
    message = db.Column(db.String(255), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False, index=True)
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=trinidad_now, index=True)
    
    # Add constraints and indexes
    __table_args__ = (
        db.CheckConstraint("notification_type IN ('approval', 'clock_in', 'clock_out', 'schedule', 'reminder', 'request', 'missed', 'update')", 
                          name='check_valid_notification_type'),
        db.Index('idx_notification_user_read', 'username', 'is_read'),
        db.Index('idx_notification_type_created', 'notification_type', 'created_at'),
    )
    
    # Relationships
    user = db.relationship('User', backref=db.backref('notifications', lazy=True, cascade="all, delete-orphan"))
    
    # Notification types
    TYPE_APPROVAL = 'approval'
    TYPE_CLOCK_IN = 'clock_in'
    TYPE_CLOCK_OUT = 'clock_out'
    TYPE_SCHEDULE = 'schedule'
    TYPE_REMINDER = 'reminder'
    TYPE_REQUEST = 'request'
    TYPE_MISSED = 'missed'
    TYPE_UPDATE = 'update'
    
    def __init__(self, username, message, notification_type):
        self.username = username
        self.message = message
        self.notification_type = notification_type
        self.is_read = False
    
    def get_json(self):
        return {
            'id': self.id,
            'username': self.username,
            'message': self.message,
            'notification_type': self.notification_type,
            'is_read': self.is_read,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'friendly_time': self.get_friendly_time()
        }
    
    def get_friendly_time(self):
        """Return a human-friendly time format like 'Monday at 3:00 PM'"""
        now = trinidad_now()
        diff = now - self.created_at
        
        if diff.days == 0:
            # Today
            return f"Today at {self.created_at.strftime('%I:%M %p')}"
        elif diff.days == 1:
            # Yesterday
            return f"Yesterday at {self.created_at.strftime('%I:%M %p')}"
        elif diff.days < 7:
            # This week
            return f"{self.created_at.strftime('%A')} at {self.created_at.strftime('%I:%M %p')}"
        else:
            # Older
            return f"{self.created_at.strftime('%B %d, %Y')} at {self.created_at.strftime('%I:%M %p')}"
    
    def mark_as_read(self):
        self.is_read = True
        db.session.add(self)
        db.session.commit()