from flask import Blueprint, redirect, url_for, jsonify
from flask_jwt_extended import jwt_required

index_views = Blueprint('index_views', __name__, template_folder='../templates')

@index_views.route('/', methods=['GET'])
def index_page():
    return redirect(url_for('auth_views.login_page'))

@index_views.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status':'healthy'})
