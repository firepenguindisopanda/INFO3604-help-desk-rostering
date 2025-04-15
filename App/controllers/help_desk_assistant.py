from App.models import HelpDeskAssistant
from App.database import db

def create_help_desk_assistant(username):
    new_assistant = HelpDeskAssistant(username=username)
    db.session.add(new_assistant)
    db.session.commit()
    return new_assistant


def get_help_desk_assistant(username):
    return HelpDeskAssistant.query.filter_by(username=username).first()


def get_active_help_desk_assistants():
    return HelpDeskAssistant.query.filter_by(active=True).all()
