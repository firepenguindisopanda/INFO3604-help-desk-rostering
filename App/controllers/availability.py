from App.models import Availability
from App.database import db
from datetime import datetime, time

def create_availability(username, day_of_week, start_time, end_time):
    new_availability = Availability(username, day_of_week, start_time, end_time)
    db.session.add(new_availability)
    db.session.commit()
    return new_availability


