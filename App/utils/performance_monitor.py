"""
Performance monitoring and structured logging utilities for the Help Desk Rostering system.
Implements proper observability patterns with metrics, error tracking, and structured logs.
"""

import logging
import time
import json
from functools import wraps
from datetime import datetime
from flask import request, g
from contextlib import contextmanager
from typing import Dict, Any, Optional

# Configure structured logging
class StructuredLogger:
    """Structured logger for consistent application logging"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        
    def info(self, message: str, **kwargs):
        """Log info with structured data"""
        self._log(self.logger.info, message, **kwargs)
        
    def warning(self, message: str, **kwargs):
        """Log warning with structured data"""
        self._log(self.logger.warning, message, **kwargs)
        
    def error(self, message: str, **kwargs):
        """Log error with structured data"""
        self._log(self.logger.error, message, **kwargs)
        
    def _log(self, log_func, message: str, **kwargs):
        """Internal method to format structured logs"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'message': message,
            **kwargs
        }
        
        # Add request context if available
        try:
            if hasattr(g, 'user') and g.user:
                log_data['user_id'] = getattr(g.user, 'username', 'unknown')
            if request:
                log_data['request_id'] = getattr(request, 'id', 'unknown')
                log_data['endpoint'] = request.endpoint
        except RuntimeError:
            # Outside request context
            pass
            
        log_func(json.dumps(log_data))


# Performance metrics storage (in production, use Redis or similar)
class MetricsCollector:
    """Simple metrics collector for performance monitoring"""
    
    def __init__(self):
        self.metrics = {}
        
    def record_operation(self, operation: str, duration: float, success: bool = True, **metadata):
        """Record operation metrics"""
        key = f"operation.{operation}"
        
        if key not in self.metrics:
            self.metrics[key] = {
                'count': 0,
                'total_duration': 0.0,
                'success_count': 0,
                'error_count': 0,
                'avg_duration': 0.0,
                'last_executed': None
            }
            
        self.metrics[key]['count'] += 1
        self.metrics[key]['total_duration'] += duration
        self.metrics[key]['avg_duration'] = self.metrics[key]['total_duration'] / self.metrics[key]['count']
        self.metrics[key]['last_executed'] = datetime.utcnow().isoformat()
        
        if success:
            self.metrics[key]['success_count'] += 1
        else:
            self.metrics[key]['error_count'] += 1
            
        # Add metadata
        for k, v in metadata.items():
            metric_key = f"{key}.{k}"
            if metric_key not in self.metrics:
                self.metrics[metric_key] = v
                
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics"""
        return self.metrics.copy()
        
    def get_operation_metrics(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get metrics for specific operation"""
        key = f"operation.{operation}"
        return self.metrics.get(key)


# Global instances
structured_logger = StructuredLogger('rostering_app')
metrics_collector = MetricsCollector()


def performance_monitor(operation_name: str, log_slow_threshold: float = 1.0):
    """
    Decorator to monitor performance and log slow operations with structured logging
    
    Args:
        operation_name: Name of the operation for metrics
        log_slow_threshold: Threshold in seconds to log as slow operation
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_msg = None
            
            try:
                result = func(*args, **kwargs)
                return result
                
            except Exception as e:
                success = False
                error_msg = str(e)
                structured_logger.error(
                    f"Operation {operation_name} failed",
                    operation=operation_name,
                    error=error_msg,
                    function=func.__name__
                )
                raise
                
            finally:
                duration = time.time() - start_time
                
                # Record metrics
                metadata = {
                    'function': func.__name__,
                    'args_count': len(args),
                    'kwargs_count': len(kwargs)
                }
                
                if error_msg:
                    metadata['error'] = error_msg
                    
                metrics_collector.record_operation(
                    operation_name, 
                    duration, 
                    success, 
                    **metadata
                )
                
                # Log based on performance
                if duration > log_slow_threshold:
                    structured_logger.warning(
                        f"SLOW OPERATION: {operation_name}",
                        operation=operation_name,
                        duration_seconds=round(duration, 3),
                        function=func.__name__,
                        success=success
                    )
                else:
                    structured_logger.info(
                        f"Operation completed: {operation_name}",
                        operation=operation_name,
                        duration_seconds=round(duration, 3),
                        function=func.__name__,
                        success=success
                    )
                    
        return wrapper
    return decorator


@contextmanager
def database_transaction_context(operation_name: str):
    """
    Context manager for database transactions with proper error handling and logging
    
    Usage:
        with database_transaction_context("schedule_generation"):
            # database operations here
            pass
    """
    from App.database import db
    
    start_time = time.time()
    success = True
    
    try:
        structured_logger.info(
            f"Starting database transaction: {operation_name}",
            operation=operation_name,
            transaction_type="database"
        )
        
        yield
        
        db.session.commit()
        structured_logger.info(
            f"Database transaction committed: {operation_name}",
            operation=operation_name,
            transaction_type="database",
            duration_seconds=round(time.time() - start_time, 3)
        )
        
    except Exception as e:
        success = False
        db.session.rollback()
        
        structured_logger.error(
            f"Database transaction failed: {operation_name}",
            operation=operation_name,
            transaction_type="database",
            error=str(e),
            duration_seconds=round(time.time() - start_time, 3)
        )
        
        # Record failure metrics
        metrics_collector.record_operation(
            f"db_transaction.{operation_name}", 
            time.time() - start_time, 
            success=False,
            error=str(e)
        )
        
        raise
    
    finally:
        # Record success metrics
        if success:
            metrics_collector.record_operation(
                f"db_transaction.{operation_name}", 
                time.time() - start_time, 
                success=True
            )


class QueryProfiler:
    """Helper class to profile and log slow database queries"""
    
    def __init__(self, slow_query_threshold: float = 0.5):
        self.slow_query_threshold = slow_query_threshold
        
    def profile_query(self, query_name: str):
        """Decorator to profile individual database queries"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    return result
                    
                finally:
                    duration = time.time() - start_time
                    
                    if duration > self.slow_query_threshold:
                        structured_logger.warning(
                            f"SLOW QUERY: {query_name}",
                            query_name=query_name,
                            duration_seconds=round(duration, 3),
                            function=func.__name__
                        )
                        
                    # Record query metrics
                    metrics_collector.record_operation(
                        f"query.{query_name}", 
                        duration, 
                        success=True,
                        function=func.__name__
                    )
                    
            return wrapper
        return decorator


# Global query profiler instance
query_profiler = QueryProfiler()


def get_performance_summary() -> Dict[str, Any]:
    """Get summary of application performance metrics"""
    all_metrics = metrics_collector.get_metrics()
    
    summary = {
        'timestamp': datetime.utcnow().isoformat(),
        'total_operations': 0,
        'slow_operations': [],
        'error_operations': [],
        'most_frequent_operations': [],
        'database_operations': {}
    }
    
    # Analyze metrics
    operations = []
    for key, data in all_metrics.items():
        if key.startswith('operation.') and isinstance(data, dict):
            op_name = key.replace('operation.', '')
            operations.append({
                'name': op_name,
                'count': data.get('count', 0),
                'avg_duration': data.get('avg_duration', 0),
                'error_count': data.get('error_count', 0),
                'success_rate': data.get('success_count', 0) / max(data.get('count', 1), 1) * 100
            })
            
            summary['total_operations'] += data.get('count', 0)
            
            # Identify slow operations (avg > 2 seconds)
            if data.get('avg_duration', 0) > 2.0:
                summary['slow_operations'].append({
                    'name': op_name,
                    'avg_duration': data.get('avg_duration', 0)
                })
                
            # Identify error-prone operations
            if data.get('error_count', 0) > 0:
                summary['error_operations'].append({
                    'name': op_name,
                    'error_count': data.get('error_count', 0),
                    'error_rate': data.get('error_count', 0) / max(data.get('count', 1), 1) * 100
                })
    
    # Sort by frequency
    operations.sort(key=lambda x: x['count'], reverse=True)
    summary['most_frequent_operations'] = operations[:10]
    
    # Database operations summary
    db_ops = [op for op in operations if op['name'].startswith('db_transaction.')]
    summary['database_operations'] = {
        'total_transactions': sum(op['count'] for op in db_ops),
        'avg_transaction_time': sum(op['avg_duration'] for op in db_ops) / max(len(db_ops), 1),
        'failed_transactions': sum(op['error_count'] for op in db_ops)
    }
    
    return summary


def log_performance_summary():
    """Log current performance summary"""
    summary = get_performance_summary()
    structured_logger.info("Performance Summary", **summary)
    return summary