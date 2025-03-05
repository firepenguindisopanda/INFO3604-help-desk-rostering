from App.database import db

class Schedule(db.Model):
    __tablename__ = 'schedule'
    
    id = db.Column(db.Integer, primary_key=True)
    week = db.Column(db.Integer, nullable=False)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    
    def __init__(self, week, start, end):
        self.week = week
        self.start = start
        self.end = end
    
    def get_json(self):
        return {
            'Schedule ID': self.id,
            'Week': self.week,
            'Start Date': self.start,
            'End Date': self.end
        }    
