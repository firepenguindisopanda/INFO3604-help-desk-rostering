from flask import flash, redirect, url_for, request
from flask_admin.contrib.sqla import ModelView
from flask_jwt_extended import jwt_required, current_user, unset_jwt_cookies, set_access_cookies
from flask_admin import Admin, AdminIndexView, expose
from App.models import db, User

class AdminView(ModelView):
    @jwt_required()
    def is_accessible(self):
        return current_user is not None and current_user.is_admin()

    def inaccessible_callback(self, name, **kwargs):
        flash("You don't have permission to access this resource", "error")
        return redirect(url_for('auth_views.login_page'))

class SecureAdminIndexView(AdminIndexView):
    @expose('/')
    @jwt_required()
    def index(self):
        if not current_user or not current_user.is_admin():
            flash("You don't have permission to access the admin panel", "error")
            return redirect(url_for('auth_views.login_page'))
        return super(SecureAdminIndexView, self).index()

def setup_admin(app):
    admin = Admin(app, name='Help Desk Admin', 
                 template_mode='bootstrap3', 
                 index_view=SecureAdminIndexView())
    admin.add_view(AdminView(User, db.session))