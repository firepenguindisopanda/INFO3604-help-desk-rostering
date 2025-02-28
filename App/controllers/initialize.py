from .user import create_user
from App.database import db

def initialize():
    db.drop_all()
    db.create_all()
    
    # Create default admin account
    admin = create_user('admin', 'admin123')
    
    # Create default assistant account
    assistant = create_user('816000000', 'assistant123')

    print('Database initialized with default accounts:')
    print(admin.get_json())
    print(assistant.get_json())