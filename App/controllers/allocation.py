from App.models import Allocation
from App.database import db

def create_allocation(username, schedule, shift):
    new_allocation = Allocation(username, schedule, shift)
    db.session.add(new_allocation)
    db.session.commit()
    return new_allocation
