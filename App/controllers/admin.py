from App.models import Admin
from App.database import db

def create_admin(username, password, role):
    new_admin = Admin(username, password, role)
    db.session.add(new_admin)
    db.session.commit()
    return new_admin
