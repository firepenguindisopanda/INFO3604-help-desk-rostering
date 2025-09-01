from flask import Blueprint, redirect, url_for, jsonify
from flask_jwt_extended import jwt_required
from App.controllers import create_user, initialize
from App.models import User, Student, HelpDeskAssistant, LabAssistant, Course, CourseCapability, Availability
from App.database import db
from App.middleware import admin_required
from App.models import User, Student, HelpDeskAssistant, LabAssistant, Course, CourseCapability, Availability
from App.database import db
from App.middleware import admin_required

index_views = Blueprint('index_views', __name__, template_folder='../templates')

@index_views.route('/', methods=['GET'])
def index_page():
    return redirect(url_for('auth_views.login_page'))

@index_views.route('/init', methods=['GET'])
def init():
    initialize()
    return jsonify(message='db initialized!')

@index_views.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status':'healthy'})

@index_views.route('/debug/data', methods=['GET'])
def debug_data():
    """Debug route to view all created data"""
    try:
        # Get all users
        users = User.query.all()
        user_data = []
        for user in users:
            user_data.append(user)

        # Get all students
        students = Student.query.all()
        student_data = []
        for student in students:
            student_data.append(student)
        
        # Get all courses
        courses = Course.query.all()
        course_data = []
        for course in courses:
            course_data.append(course)
        
        # Get all help desk assistants
        hd_assistants = HelpDeskAssistant.query.all()
        hd_data = []
        for assistant in hd_assistants:
            hd_data.append(assistant)
        
        # Get all lab assistants
        lab_assistants = LabAssistant.query.all()
        lab_data = []
        for assistant in lab_assistants:
            lab_data.append(assistant)

        # Get course capabilities
        capabilities = CourseCapability.query.all()
        capability_data = []
        for cap in capabilities:
            capability_data.append(cap)

        # Get availabilities
        availabilities = Availability.query.all()
        availability_data = []
        for avail in availabilities:
            availability_data.append(avail)

        
        # Get counts
        data_summary = {
            'users': len(user_data),
            'students': len(student_data),
            'courses': len(course_data),
            'help_desk_assistants': len(hd_data),
            'lab_assistants': len(lab_data),
            'course_capabilities': len(capability_data),
            'availabilities': len(availability_data)
        }
        
        return jsonify({
            'summary': data_summary,
            'users': user_data,
            'students': student_data,
            'courses': course_data,
            'help_desk_assistants': hd_data,
            'lab_assistants': lab_data,
            'course_capabilities': capability_data,
            'availabilities': availability_data
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Error retrieving debug data'
        }), 500


@index_views.route('/debug/init', methods=['GET'])
def debug_init():
    """Debug route to manually initialize the database"""
    try:
        from App.controllers import initialize
        from App.database import db
        from flask import current_app
        
        # Create tables first
        with current_app.app_context():
            db.create_all()
            print("Tables created")
            
            # Then initialize data
            initialize()
            print("Data initialized")
        
        return jsonify({
            'message': 'Database initialized successfully',
            'status': 'ok'
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Error initializing database'
        }), 500