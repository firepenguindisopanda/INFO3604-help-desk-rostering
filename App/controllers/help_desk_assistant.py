from App.models import HelpDeskAssistant
from App.database import db

def create_lab_assistant(username):
    new_assistant = HelpDeskAssistant(username=username)
    db.session.add(new_assistant)
    db.session.commit()
    return new_assistant

def get_lab_assistant(username):
    return HelpDeskAssistant.query.filter_by(username=username).first()