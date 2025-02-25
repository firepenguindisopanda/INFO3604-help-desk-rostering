from flask import Blueprint, render_template
from flask_jwt_extended import jwt_required

requests_views = Blueprint('requests_views', __name__, template_folder='../templates')

@requests_views.route('/requests')
@jwt_required()
def requests():
    return render_template('admin/requests/index.html')