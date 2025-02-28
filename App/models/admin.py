from App.database import db
from .user import User

class Admin(User):
    __tablename__ = 'admin'
    
    username = db.Column(db.String(20), db.ForeignKey('user.username'), primary_key=True)
    
    __mapper_args__ = {
        'polymorphic_identity': 'admin'
    }
    
    def init(self, username, password):
        super().__init__(username, password)
    
    def get_json(self):
        return {
            'Admin ID': self.username
        }
    
    