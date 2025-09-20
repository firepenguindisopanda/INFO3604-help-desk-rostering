from App.database import db
from datetime import datetime
from App.utils.time_utils import trinidad_now, convert_to_trinidad_time

class Request(db.Model):
    __tablename__ = 'request'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), db.ForeignKey('student.username', ondelete='CASCADE'), nullable=False, index=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id', ondelete='CASCADE'), nullable=True, index=True)
    date = db.Column(db.DateTime, nullable=True, index=True)
    time_slot = db.Column(db.String(50), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    replacement = db.Column(db.String(20), db.ForeignKey('student.username', ondelete='SET NULL'), nullable=True, index=True)
    status = db.Column(db.String(20), default='PENDING', index=True)  # PENDING, APPROVED, REJECTED, CANCELLED
    created_at = db.Column(db.DateTime, default=trinidad_now(), index=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    
    # Add constraints and indexes
    __table_args__ = (
        db.CheckConstraint("status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')", name='check_valid_request_status'),
        db.Index('idx_request_user_status', 'username', 'status'),
        db.Index('idx_request_shift_status', 'shift_id', 'status'),
        db.Index('idx_request_date_status', 'date', 'status'),
    )
    
    # Relationships
    student = db.relationship('Student', foreign_keys=[username], 
                              backref=db.backref('requests', lazy=True, cascade="all, delete-orphan"))
    replacement_student = db.relationship('Student', foreign_keys=[replacement])
    shift = db.relationship('Shift', backref=db.backref('requests', lazy=True))
    
    def __init__(self, username, time_slot, reason, status='PENDING', shift_id=None, 
                 date=None, replacement=None):
        self.username = username
        self.shift_id = shift_id
        self.date = date
        self.time_slot = time_slot
        self.reason = reason
        self.replacement = replacement
        self.status = status
    
    def approve(self):
        """Approve this request"""
        self.status = 'APPROVED'
        self.approved_at = trinidad_now()
        return self
    
    def reject(self):
        """Reject this request"""
        self.status = 'REJECTED' 
        self.rejected_at = trinidad_now()
        return self
    
    def cancel(self):
        """Cancel this request (only valid for pending requests)"""
        if self.status != 'PENDING':
            return False
        self.status = 'CANCELLED'
        return True
    
    def get_json(self):
        """Return a JSON-serializable representation of this request"""
        return {
            'id': self.id,
            'username': self.username,
            'shift_id': self.shift_id,
            'date': self.date.strftime('%Y-%m-%d') if self.date else None,
            'time_slot': self.time_slot,
            'reason': self.reason,
            'replacement': self.replacement,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'approved_at': self.approved_at.strftime('%Y-%m-%d %H:%M:%S') if self.approved_at else None,
            'rejected_at': self.rejected_at.strftime('%Y-%m-%d %H:%M:%S') if self.rejected_at else None
        }
    
    def get_formatted_time(self):
        """Return a human-friendly format for the time slot"""
        if self.date:
            return f"{self.date.strftime('%A, %B %d')}: {self.time_slot}"
        return self.time_slot