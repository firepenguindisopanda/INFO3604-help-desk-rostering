from App.models import Shift
from App.database import db
from datetime import datetime, time

def create_shift(date, start_time, end_time, schedule_id):
    new_shift = Shift(date=date, start_time=start_time, end_time=end_time, schedule_id=schedule_id)
    db.session.add(new_shift)
    db.session.commit()
    return new_shift
