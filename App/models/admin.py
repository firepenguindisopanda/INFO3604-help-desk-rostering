from App.database import db
from .user import User

class Admin(User):
    __tablename__ = 'admin'
    
    username = db.Column(db.String(20), db.ForeignKey('users.username', ondelete='CASCADE'), primary_key=True)
    role = db.Column(db.String(20), nullable=False, index=True)
    
    __mapper_args__ = {
        'polymorphic_identity': 'admin'
    }
    
    def __init__(self, username, password, role):
        super().__init__(username, password, type='admin')
        self.role = role
    
    def get_json(self):
        return {
            'Admin ID': self.username,
            'Role': self.role
        }
    
    def to_dict(self):
        """Convert admin to dictionary for API responses (excludes password)"""
        base_dict = super().to_dict()
        base_dict.update({
            'role': self.role,
            'admin_type': self.role
        })
        return base_dict