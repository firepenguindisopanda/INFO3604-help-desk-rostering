import logging

from flask import request
from sqlalchemy import text
from flask_jwt_extended import jwt_required

from App.views.api_v2 import api_v2
from App.views.api_v2.utils import (
    api_success,
    api_error,
    jwt_required_secure,
)
from App.middleware import admin_required
from App.utils.performance_monitor import (
    get_performance_summary,
    log_performance_summary,
    metrics_collector,
)
from App.database import db

logger = logging.getLogger(__name__)


@api_v2.route('/admin/performance/metrics', methods=['GET'])
@jwt_required()
@admin_required
def api_get_performance_metrics():
    """Return summarized performance metrics for admin dashboards."""
    try:
        summary = get_performance_summary()
        logger.info('Metrics summary: %s', summary)
        return api_success(data=summary)
    except Exception as exc:
        logger.exception('API v2: Failed to retrieve performance metrics')
        return api_error(
            'Failed to retrieve performance metrics',
            errors={'detail': str(exc)},
            status_code=500,
        )


@api_v2.route('/admin/performance/slow-operations', methods=['GET'])
@jwt_required()
@admin_required
def api_get_slow_operations():
    """Return slow operations along with optimization recommendations."""
    try:
        summary = get_performance_summary()
        logger.info('Performance summary: %s', summary)
        slow_ops = summary.get('slow_operations', [])

        for op in slow_ops:
            op['recommendations'] = _get_optimization_recommendations(op.get('name'))

        return api_success(
            data={
                'slow_operations': slow_ops,
                'count': len(slow_ops),
                'threshold': '2.0 seconds average',
            }
        )
    except Exception as exc:
        logger.exception('API v2: Failed to retrieve slow operations')
        return api_error(
            'Failed to retrieve slow operations',
            errors={'detail': str(exc)},
            status_code=500,
        )


@api_v2.route('/admin/performance/health', methods=['GET'])
@jwt_required()
@admin_required
def api_performance_health_check():
    """Public health check for performance subsystem."""
    try:
        db.session.execute(text('SELECT 1'))

        summary = get_performance_summary()
        total_ops = summary.get('total_operations', 0) or 0
        slow_ops = summary.get('slow_operations', []) or []
        error_ops = summary.get('error_operations', []) or []

        health_status = {
            'status': 'healthy',
            'database': 'connected',
            'total_operations': total_ops,
            'slow_operations_count': len(slow_ops),
            'error_operations_count': len(error_ops),
        }

        if total_ops > 0:
            error_rate = (len(error_ops) / max(total_ops, 1)) * 100
            if error_rate > 10 or len(slow_ops) > 3:
                health_status['status'] = 'degraded'

        status_code = 200 if health_status['status'] == 'healthy' else 503
        return api_success(data=health_status, status_code=status_code)
    except Exception as exc:
        logger.exception('API v2: Performance health check failed')
        return api_error(
            'Performance subsystem unhealthy',
            errors={'detail': str(exc)},
            status_code=503,
        )


@api_v2.route('/admin/performance/log-summary', methods=['POST'])
@jwt_required()
@admin_required
def api_log_performance_summary():
    """Trigger logging of current performance summary."""
    try:
        summary = log_performance_summary()
        logger.info('Logged performance summary: %s', summary)
        return api_success(
            data=summary,
            message='Performance summary logged',
        )
    except Exception as exc:
        logger.exception('API v2: Failed to log performance summary')
        return api_error(
            'Failed to log performance summary',
            errors={'detail': str(exc)},
            status_code=500,
        )


def _get_optimization_recommendations(operation_name):
    """Return optimization tips for a particular operation."""
    recommendations = {
        'generate_help_desk_schedule': [
            'Consider reducing the number of course demands per shift',
            'Pre-load staff availability data',
            'Use batch database operations',
            'Optimize constraint solver parameters',
        ],
        'get_schedule_data': [
            'Use eager loading with selectinload',
            'Cache frequently accessed schedule data',
            'Reduce the number of database queries per shift',
        ],
        'get_current_schedule': [
            'Implement eager loading for relationships',
            'Cache the formatted schedule data',
            'Use database-level filtering instead of Python loops',
        ],
        'schedule_viewing': [
            'Add database indexes for common queries',
            'Use pagination for large datasets',
            'Implement client-side caching',
        ],
    }

    return recommendations.get(
        operation_name,
        [
            'Review database queries for N+1 issues',
            'Consider adding database indexes',
            'Implement caching where appropriate',
            'Use batch operations instead of individual queries',
        ],
    )
