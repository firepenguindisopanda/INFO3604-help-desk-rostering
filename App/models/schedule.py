from App.database import db

class Schedule(db.Model):
    __tablename__ = 'schedule'
    
    id = db.Column(db.Integer, primary_key=True)
    week = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    
    def __init__(self, week, start_date):
        self.week = week
        self.start_date = start_date
    
    def get_json(self):
        return {
            'Schedule ID': self.id,
            'Week': self.week,
            'Start Date': self.start
        }    
