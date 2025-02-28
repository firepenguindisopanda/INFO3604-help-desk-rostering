from App.database import db
from .user import User

class Admin(User):
    __tablename__ = 'admin'
    
    def init(self, username, password):
        super().__init__(username, password)
    
    def get_json(self):
        return {
            'Admin ID': self.username
        }
    
    