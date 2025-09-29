"""
Performance monitoring endpoints for the Help Desk Rostering system.
Provides admin access to performance metrics and system health.
"""

from flask import Blueprint, jsonify, render_template
from flask_jwt_extended import jwt_required
from App.middleware import admin_required
from App.utils.performance_monitor import (
    get_performance_summary,
    log_performance_summary,
    metrics_collector
)
import logging

logger = logging.getLogger(__name__)

# Create blueprint for performance monitoring
performance_bp = Blueprint('performance', __name__, url_prefix='/admin/performance')


@performance_bp.route('/metrics', methods=['GET'])
@jwt_required()
@admin_required
def get_metrics():
    """Get current performance metrics"""
    try:
        summary = get_performance_summary()
        return jsonify({
            'status': 'success',
            'data': summary
        })
    except Exception as e:
        logger.error(f"Error retrieving performance metrics: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve performance metrics'
        }), 500


@performance_bp.route('/metrics/raw', methods=['GET'])
@jwt_required()
@admin_required
def get_raw_metrics():
    """Get raw performance metrics data"""
    try:
        raw_metrics = metrics_collector.get_metrics()
        return jsonify({
            'status': 'success',
            'data': raw_metrics
        })
    except Exception as e:
        logger.error(f"Error retrieving raw metrics: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve raw metrics'
        }), 500


@performance_bp.route('/dashboard')
@jwt_required()
@admin_required
def performance_dashboard():
    """Render performance monitoring dashboard"""
    try:
        return render_template('admin/performance/dashboard.html')
    except Exception as e:
        logger.error(f"Error loading performance dashboard: {str(e)}")
        return render_template('errors/500.html'), 500


@performance_bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    try:
        from App.database import db
        
        # Test database connection
        db.session.execute('SELECT 1')
        
        # Get basic system metrics
        summary = get_performance_summary()
        
        health_status = {
            'status': 'healthy',
            'database': 'connected',
            'total_operations': summary.get('total_operations', 0),
            'slow_operations_count': len(summary.get('slow_operations', [])),
            'error_operations_count': len(summary.get('error_operations', []))
        }
        
        # Determine overall health
        if summary.get('total_operations', 0) > 0:
            error_rate = len(summary.get('error_operations', [])) / summary.get('total_operations', 1) * 100
            if error_rate > 10:  # More than 10% error rate
                health_status['status'] = 'degraded'
            elif len(summary.get('slow_operations', [])) > 3:  # Too many slow operations
                health_status['status'] = 'degraded'
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503


@performance_bp.route('/log-summary', methods=['POST'])
@jwt_required()
@admin_required
def log_summary():
    """Manually trigger performance summary logging"""
    try:
        summary = log_performance_summary()
        return jsonify({
            'status': 'success',
            'message': 'Performance summary logged',
            'data': summary
        })
    except Exception as e:
        logger.error(f"Error logging performance summary: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to log performance summary'
        }), 500


@performance_bp.route('/slow-operations', methods=['GET'])
@jwt_required()
@admin_required
def get_slow_operations():
    """Get list of slow operations for optimization"""
    try:
        summary = get_performance_summary()
        slow_ops = summary.get('slow_operations', [])
        
        # Add recommendations for each slow operation
        for op in slow_ops:
            op['recommendations'] = get_optimization_recommendations(op['name'])
        
        return jsonify({
            'status': 'success',
            'data': {
                'slow_operations': slow_ops,
                'count': len(slow_ops),
                'threshold': '2.0 seconds average'
            }
        })
    except Exception as e:
        logger.error(f"Error retrieving slow operations: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve slow operations'
        }), 500


def get_optimization_recommendations(operation_name):
    """Get optimization recommendations for specific operations"""
    recommendations = {
        'generate_help_desk_schedule': [
            'Consider reducing the number of course demands per shift',
            'Pre-load staff availability data',
            'Use batch database operations',
            'Optimize constraint solver parameters'
        ],
        'get_schedule_data': [
            'Use eager loading with selectinload',
            'Cache frequently accessed schedule data',
            'Reduce the number of database queries per shift'
        ],
        'get_current_schedule': [
            'Implement eager loading for relationships',
            'Cache the formatted schedule data',
            'Use database-level filtering instead of Python loops'
        ],
        'schedule_viewing': [
            'Add database indexes for common queries',
            'Use pagination for large datasets',
            'Implement client-side caching'
        ]
    }
    
    return recommendations.get(operation_name, [
        'Review database queries for N+1 issues',
        'Consider adding database indexes',
        'Implement caching where appropriate',
        'Use batch operations instead of individual queries'
    ])