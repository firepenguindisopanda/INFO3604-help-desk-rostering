from App.database import db

class Course(db.Model):
    __tablename__ = 'course'
    
    code = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    def __init__(self, code, name):
        self.code = code
        self.name = name
    
    def get_json(self):
        return {
            self.code: self.name,
        }