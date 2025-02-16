from .user import create_user
from App.database import db

def initialize():
    db.drop_all()
    db.create_all()
    
    # Create default admin account
    create_user('admin', 'admin123')
    
    # Create default assistant account
    create_user('816000000', 'assistant123')

    print('Database initialized with default accounts:')
    print('Admin - username: admin, password: admin123')
    print('Assistant - username: 816000000, password: assistant123')