from App.models import User
from App.database import db

def create_user(username, password, type='student'):
    newuser = User(username=username, password=password, type=type)
    db.session.add(newuser)
    db.session.commit()
    return newuser

def get_user(username):
    return User.query.filter_by(username=username).first()

def get_all_users():
    return User.query.all()

def get_all_users_json():
    users = User.query.all()
    if not users:
        return []
    users = [user.get_json() for user in users]
    return users

def update_user(username, new_username):
    user = get_user(username)
    if user:
        user.username = new_username
        db.session.add(user)
        return db.session.commit()
    return None
