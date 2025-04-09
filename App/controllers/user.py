from App.models import User, Student, HelpDeskAssistant,CourseCapability, Availability
from App.controllers import create_admin, create_student
from App.database import db

def create_user(username, password, type='student'):
    if type == 'student':
        user = create_student(username, password, "BSc", "Unnamed")
    else:
        user = create_admin(username, password)
    return user

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
        db.session.commit()  # Commit the changes to the database
        return user
    return None

def get_user_profile(username):
    """Get a user's detailed profile information"""
    user = get_user(username)
    if not user:
        return None
        
    profile = {
        'username': user.username,
        'type': user.type
    }
    
    # Add specific details based on user type
    if user.type == 'student':
        student = Student.query.get(username)
        if student:
            profile.update({
                'name': student.name,
                'degree': student.degree
            })
            
            # Get help desk assistant details if they exist
            assistant = HelpDeskAssistant.query.get(username)
            if assistant:
                profile.update({
                    'rate': assistant.rate,
                    'active': assistant.active,
                    'hours_worked': assistant.hours_worked,
                    'hours_minimum': assistant.hours_minimum
                })
                
                # Get course capabilities
                course_capabilities = CourseCapability.query.filter_by(assistant_username=username).all()
                profile['courses'] = [cap.course_code for cap in course_capabilities]
                
                # Get availabilities
                availabilities = Availability.query.filter_by(username=username).all()
                profile['availabilities'] = [availability.get_json() for availability in availabilities]
    
    return profile
