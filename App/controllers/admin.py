from App.models import Admin
from App.database import db

def create_admin(username, password):
    new_admin = Admin(username, password)
    db.session.add(new_admin)
    db.session.commit()
    return new_admin
