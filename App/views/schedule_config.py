from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user
from App.controllers import schedule_config as config_controller
from App.middleware import admin_required
import logging

logger = logging.getLogger(__name__)

schedule_config_views = Blueprint('schedule_config_views', __name__, template_folder='../templates')


@schedule_config_views.route('/admin/schedule-config')
@jwt_required()
@admin_required
def schedule_config():
    """
    Render the schedule configuration page for admins.
    
    This page allows administrators to:
    - Create new schedule configurations
    - Edit existing configurations  
    - Preview generated shifts
    - Activate/deactivate configurations
    - Delete configurations
    
    Returns:
        Rendered template for schedule configuration management
    """
    try:
        # Get active configuration for display
        active_config = config_controller.get_active_config()
        
        return render_template('schedule_config.html', 
                             active_config=active_config,
                             page_title="Schedule Configuration")
    
    except Exception as e:
        logger.error(f"Error loading schedule config page: {e}")
        flash("Error loading schedule configuration page", "danger")
        return redirect(url_for('admin.index'))


@schedule_config_views.route('/admin/schedule-config/quick-setup')
@jwt_required()
@admin_required  
def quick_setup():
    """
    Quick setup page for creating the default configuration.
    
    Returns:
        Redirect to main config page with success/error message
    """
    try:
        # Check if default config already exists
        existing_configs = config_controller.get_all_schedule_configs()
        default_exists = any(config.name == "Default Help Desk Schedule" for config in existing_configs)
        
        if default_exists:
            flash("Default configuration already exists", "info")
        else:
            # Create default configuration
            config = config_controller.create_default_config()
            flash(f"Default configuration '{config.name}' created successfully", "success")
        
        return redirect(url_for('schedule_config_views.schedule_config'))
    
    except Exception as e:
        logger.error(f"Error creating default config: {e}")
        flash("Failed to create default configuration", "danger")
        return redirect(url_for('schedule_config_views.schedule_config'))


@schedule_config_views.route('/admin/schedule-config/help')
@jwt_required()
@admin_required
def configuration_help():
    """
    Help page explaining schedule configuration options.
    
    Returns:
        Rendered help template
    """
    return render_template('schedule_config_help.html', 
                         page_title="Schedule Configuration Help")


# Error handlers for this blueprint
@schedule_config_views.errorhandler(404)
def config_not_found(error):
    """Handle 404 errors within schedule config views."""
    flash("Schedule configuration page not found", "danger")
    return redirect(url_for('admin.index'))


@schedule_config_views.errorhandler(500)
def config_server_error(error):
    """Handle 500 errors within schedule config views."""
    logger.error(f"Server error in schedule config views: {error}")
    flash("Internal server error in schedule configuration", "danger")
    return redirect(url_for('admin.index'))