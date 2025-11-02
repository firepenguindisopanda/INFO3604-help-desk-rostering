from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import time
from App.views.api_v2 import api_v2
from App.views.api_v2.utils import api_success, api_error, validate_json_request_secure, jwt_required_secure
from App.controllers import schedule_config as config_controller
from App.models import ScheduleConfig
from App.database import db
import logging

logger = logging.getLogger(__name__)


@api_v2.route('/schedule-config', methods=['GET'])
@jwt_required_secure()
def get_schedule_configs():
    """
    Get all schedule configurations
    
    Returns:
        Success: List of all schedule configurations
        Error: Server error message
    """
    try:
        configs = config_controller.get_all_schedule_configs()
        configs_data = [config.to_dict() for config in configs]
        
        return api_success(configs_data, "Schedule configurations retrieved successfully")
        
    except Exception as e:
        logger.error(f"Failed to retrieve schedule configs: {e}")
        return api_error(f"Failed to retrieve schedule configurations: {str(e)}", status_code=500)


@api_v2.route('/schedule-config', methods=['POST'])
@jwt_required_secure()
def create_schedule_config():
    """
    Create a new schedule configuration
    
    Expected JSON body:
    {
        "name": "Default Help Desk Schedule",
        "operating_days": [0, 1, 2],
        "start_time": "10:00",
        "end_time": "14:00",
        "shift_duration_minutes": 60,
        "staff_per_shift": 1,
        "is_active": true
    }
    
    Returns:
        Success: Created configuration data
        Error: Validation or creation error
    """
    data, error = validate_json_request_secure(required_fields=[
        'name', 'operating_days', 'start_time', 'end_time'
    ])
    if error:
        return error
    
    try:
        # Parse and validate time strings
        start_time = time.fromisoformat(data['start_time'])
        end_time = time.fromisoformat(data['end_time'])
        
        # Create configuration using controller
        config = config_controller.create_schedule_config(
            name=data['name'],
            operating_days=data['operating_days'],
            start_time=start_time,
            end_time=end_time,
            shift_duration_minutes=data.get('shift_duration_minutes', 60),
            staff_per_shift=data.get('staff_per_shift', 1),
            is_active=data.get('is_active', True)
        )
        
        return api_success(config.to_dict(), "Schedule configuration created successfully", status_code=201)
        
    except ValueError as e:
        return api_error(f"Validation error: {str(e)}", status_code=400)
    except Exception as e:
        logger.error(f"Failed to create schedule config: {e}")
        return api_error(f"Failed to create schedule configuration: {str(e)}", status_code=500)


@api_v2.route('/schedule-config/<int:config_id>', methods=['GET'])
@jwt_required_secure()
def get_schedule_config(config_id):
    """
    Get a specific schedule configuration by ID
    
    Args:
        config_id: Configuration ID
    
    Returns:
        Success: Configuration data
        Error: Configuration not found
    """
    try:
        config = config_controller.get_schedule_config(config_id)
        
        if not config:
            return api_error(f"Schedule configuration with ID {config_id} not found", status_code=404)
        
        return api_success(config.to_dict(), "Schedule configuration retrieved successfully")
        
    except Exception as e:
        logger.error(f"Failed to retrieve schedule config {config_id}: {e}")
        return api_error(f"Failed to retrieve schedule configuration: {str(e)}", status_code=500)


@api_v2.route('/schedule-config/<int:config_id>', methods=['PUT'])
@jwt_required_secure()
def update_schedule_config(config_id):
    """
    Update a schedule configuration
    
    Args:
        config_id: Configuration ID to update
        
    Expected JSON body (all fields optional):
    {
        "name": "Updated Schedule Name",
        "operating_days": [0, 1, 2, 3, 4],
        "start_time": "09:00",
        "end_time": "17:00",
        "shift_duration_minutes": 120,
        "staff_per_shift": 2,
        "is_active": false
    }
    
    Returns:
        Success: Updated configuration data
        Error: Configuration not found or update error
    """
    data, error = validate_json_request_secure()
    if error:
        return error
    
    try:
        # Parse time fields if provided
        update_data = {}
        for key, value in data.items():
            if key in ['start_time', 'end_time'] and value:
                update_data[key] = time.fromisoformat(value)
            else:
                update_data[key] = value
        
        config = config_controller.update_schedule_config(config_id, **update_data)
        
        return api_success(config.to_dict(), "Schedule configuration updated successfully")
        
    except ValueError as e:
        return api_error(f"Validation error: {str(e)}", status_code=400)
    except Exception as e:
        logger.error(f"Failed to update schedule config {config_id}: {e}")
        if "not found" in str(e).lower():
            return api_error(f"Schedule configuration with ID {config_id} not found", status_code=404)
        return api_error(f"Failed to update schedule configuration: {str(e)}", status_code=500)


@api_v2.route('/schedule-config/<int:config_id>', methods=['DELETE'])
@jwt_required_secure()
def delete_schedule_config(config_id):
    """
    Delete a schedule configuration
    
    Args:
        config_id: Configuration ID to delete
    
    Returns:
        Success: Deletion confirmation
        Error: Configuration not found or deletion error
    """
    try:
        success = config_controller.delete_schedule_config(config_id)
        
        if not success:
            return api_error(f"Schedule configuration with ID {config_id} not found", status_code=404)
        
        return api_success(message=f"Schedule configuration {config_id} deleted successfully")
        
    except Exception as e:
        logger.error(f"Failed to delete schedule config {config_id}: {e}")
        return api_error(f"Failed to delete schedule configuration: {str(e)}", status_code=500)


@api_v2.route('/schedule-config/active', methods=['GET'])
@jwt_required_secure()
def get_active_config():
    """
    Get the currently active schedule configuration
    
    Returns:
        Success: Active configuration data
        Error: No active configuration found
    """
    try:
        config = config_controller.get_active_config()
        
        if not config:
            return api_error('No active schedule configuration found', status_code=404)
        
        return api_success(config.to_dict(), "Active schedule configuration retrieved successfully")
        
    except Exception as e:
        logger.error(f"Failed to retrieve active config: {e}")
        return api_error(f"Failed to retrieve active configuration: {str(e)}", status_code=500)


@api_v2.route('/schedule-config/<int:config_id>/activate', methods=['POST'])
@jwt_required_secure()
def activate_config(config_id):
    """
    Activate a specific schedule configuration
    
    Args:
        config_id: Configuration ID to activate
    
    Returns:
        Success: Activated configuration data
        Error: Configuration not found or activation error
    """
    try:
        config = config_controller.activate_config(config_id)
        
        return api_success(config.to_dict(), "Schedule configuration activated successfully")
        
    except Exception as e:
        logger.error(f"Failed to activate config {config_id}: {e}")
        if "not found" in str(e).lower():
            return api_error(f"Schedule configuration with ID {config_id} not found", status_code=404)
        return api_error(f"Failed to activate schedule configuration: {str(e)}", status_code=500)


@api_v2.route('/schedule-config/<int:config_id>/preview-shifts', methods=['GET'])
@jwt_required_secure()
def preview_shifts(config_id):
    """
    Preview the shifts that would be generated from a configuration
    
    Args:
        config_id: Configuration ID to preview
    
    Returns:
        Success: Generated shifts data
        Error: Configuration not found or generation error
    """
    try:
        config = config_controller.get_schedule_config(config_id)
        
        if not config:
            return api_error(f"Schedule configuration with ID {config_id} not found", status_code=404)
        
        shifts = config_controller.generate_shifts_from_config(config)
        summary = config_controller.get_config_summary(config)
        
        return api_success({
            'config': config.to_dict(),
            'generated_shifts': shifts,
            'summary': summary
        }, "Shifts preview generated successfully")
        
    except Exception as e:
        logger.error(f"Failed to preview shifts for config {config_id}: {e}")
        return api_error(f"Failed to generate shifts preview: {str(e)}", status_code=500)


@api_v2.route('/schedule-config/default', methods=['POST'])
@jwt_required_secure()
def create_default_config():
    """
    Create the default schedule configuration
    (Monday-Wednesday, 10 AM - 2 PM, 1-hour shifts, 1 person per shift)
    
    Returns:
        Success: Created default configuration
        Error: Creation error
    """
    try:
        config = config_controller.create_default_config()
        
        return api_success(config.to_dict(), "Default schedule configuration created successfully", status_code=201)
        
    except Exception as e:
        logger.error(f"Failed to create default config: {e}")
        return api_error(f"Failed to create default configuration: {str(e)}", status_code=500)


@api_v2.route('/schedule-config/summary', methods=['GET'])
@jwt_required_secure()
def get_all_configs_summary():
    """
    Get a summary of all schedule configurations with shift counts
    
    Returns:
        Success: List of configuration summaries
        Error: Server error
    """
    try:
        configs = config_controller.get_all_schedule_configs()
        summaries = []
        
        for config in configs:
            summary = config_controller.get_config_summary(config)
            summaries.append(summary)
        
        return api_success(summaries, "Configuration summaries retrieved successfully")
        
    except Exception as e:
        logger.error(f"Failed to retrieve config summaries: {e}")
        return api_error(f"Failed to retrieve configuration summaries: {str(e)}", status_code=500)