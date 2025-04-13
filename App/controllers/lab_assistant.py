from App.models import LabAssistant
from App.database import db

def create_lab_assistant(username, experience):
    new_assistant = LabAssistant(username=username, experience=bool(int(experience)))
    db.session.add(new_assistant)
    db.session.commit()
    return new_assistant


def get_lab_assistant(username):
    return LabAssistant.query.filter_by(username=username).first()

