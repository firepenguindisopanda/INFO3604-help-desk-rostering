from .user import create_user
from App.database import db

def initialize():
    db.drop_all()
    db.create_all()
    
    # Create default admin account
    create_user('admin', 'admin123', role='admin')
    
    # Create default volunteer/assistant account
    create_user('816000000', 'assistant123', role='volunteer')

    print('Database initialized with default accounts:')
    print('Admin - username: admin, password: admin123')
    print('Volunteer - username: 816000000, password: assistant123')