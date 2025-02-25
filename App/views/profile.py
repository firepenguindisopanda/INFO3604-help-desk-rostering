from flask import Blueprint, render_template
from flask_jwt_extended import jwt_required, current_user

profile_views = Blueprint('profile_views', __name__, template_folder='../templates')

@profile_views.route('/profile')
@jwt_required()
def profile():
    return render_template('admin/profile/index.html')