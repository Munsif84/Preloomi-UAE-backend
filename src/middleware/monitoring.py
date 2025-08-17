import logging
import time
import json
from functools import wraps
from flask import request, g, current_app
from datetime import datetime, timedelta
import psutil
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class MonitoringMiddleware:
    """Middleware for monitoring, logging, and performance tracking"""
    
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.response_times = []
        self.start_time = datetime.now()
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
    
    def log_request(self, request):
        """Log incoming request details"""
        logger.info(f"Request: {request.method} {request.path} | IP: {request.remote_addr} | User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
        
        # Log request body for POST/PUT requests (excluding sensitive data)
        if request.method in ['POST', 'PUT'] and request.is_json:
            data = request.get_json()
            if data:
                # Remove sensitive fields before logging
                safe_data = self._sanitize_log_data(data)
                logger.info(f"Request Body: {json.dumps(safe_data, indent=2)}")
    
    def log_response(self, response, duration):
        """Log response details"""
        self.request_count += 1
        self.response_times.append(duration)
        
        if response.status_code >= 400:
            self.error_count += 1
            logger.error(f"Response: {response.status_code} | Duration: {duration:.3f}s")
        else:
            logger.info(f"Response: {response.status_code} | Duration: {duration:.3f}s")
    
    def _sanitize_log_data(self, data):
        """Remove sensitive information from log data"""
        sensitive_fields = ['password', 'token', 'secret', 'key', 'credit_card', 'cvv']
        
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(field in key.lower() for field in sensitive_fields):
                    sanitized[key] = '[REDACTED]'
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_log_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_log_data(item) for item in data]
        else:
            return data
    
    def get_system_metrics(self):
        """Get current system performance metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3)
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {}
    
    def get_app_metrics(self):
        """Get application performance metrics"""
        uptime = datetime.now() - self.start_time
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        error_rate = (self.error_count / self.request_count * 100) if self.request_count > 0 else 0
        
        return {
            'uptime_seconds': uptime.total_seconds(),
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'error_rate_percent': error_rate,
            'average_response_time_ms': avg_response_time * 1000,
            'requests_per_minute': self.request_count / max(uptime.total_seconds() / 60, 1)
        }
    
    def log_performance_warning(self, metric_name, value, threshold):
        """Log performance warnings when thresholds are exceeded"""
        logger.warning(f"Performance Warning: {metric_name} = {value} (threshold: {threshold})")
    
    def check_performance_thresholds(self):
        """Check if any performance metrics exceed thresholds"""
        system_metrics = self.get_system_metrics()
        app_metrics = self.get_app_metrics()
        
        # Define thresholds
        thresholds = {
            'cpu_percent': 80,
            'memory_percent': 85,
            'disk_percent': 90,
            'error_rate_percent': 5,
            'average_response_time_ms': 2000
        }
        
        # Check system metrics
        for metric, threshold in thresholds.items():
            if metric in system_metrics and system_metrics[metric] > threshold:
                self.log_performance_warning(metric, system_metrics[metric], threshold)
        
        # Check app metrics
        for metric, threshold in thresholds.items():
            if metric in app_metrics and app_metrics[metric] > threshold:
                self.log_performance_warning(metric, app_metrics[metric], threshold)

# Decorators for monitoring
def monitor_performance(f):
    """Decorator to monitor function performance"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = f(*args, **kwargs)
            duration = time.time() - start_time
            
            # Log slow requests (> 1 second)
            if duration > 1.0:
                logger.warning(f"Slow request: {request.endpoint} took {duration:.3f}s")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error in {request.endpoint}: {str(e)} | Duration: {duration:.3f}s")
            raise
    
    return decorated_function

def log_user_action(action_type):
    """Decorator to log user actions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = getattr(g, 'user_id', 'anonymous')
            ip_address = request.remote_addr
            
            logger.info(f"User Action: {action_type} | User: {user_id} | IP: {ip_address} | Endpoint: {request.endpoint}")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def track_api_usage(f):
    """Decorator to track API endpoint usage"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        endpoint = request.endpoint
        method = request.method
        
        # Store usage data (in a real app, this would go to a database)
        logger.info(f"API Usage: {method} {endpoint}")
        
        return f(*args, **kwargs)
    return decorated_function

class DatabaseMonitor:
    """Monitor database performance and health"""
    
    def __init__(self, db):
        self.db = db
        self.query_count = 0
        self.slow_queries = []
    
    def log_query(self, query, duration):
        """Log database query performance"""
        self.query_count += 1
        
        if duration > 0.5:  # Log slow queries (> 500ms)
            self.slow_queries.append({
                'query': str(query),
                'duration': duration,
                'timestamp': datetime.now()
            })
            logger.warning(f"Slow Query: {duration:.3f}s | {str(query)[:100]}...")
    
    def get_db_metrics(self):
        """Get database performance metrics"""
        return {
            'total_queries': self.query_count,
            'slow_queries_count': len(self.slow_queries),
            'recent_slow_queries': self.slow_queries[-5:] if self.slow_queries else []
        }

class SecurityMonitor:
    """Monitor security events and threats"""
    
    def __init__(self):
        self.failed_logins = {}
        self.suspicious_activities = []
    
    def log_failed_login(self, ip_address, username=None):
        """Log failed login attempts"""
        if ip_address not in self.failed_logins:
            self.failed_logins[ip_address] = []
        
        self.failed_logins[ip_address].append({
            'username': username,
            'timestamp': datetime.now(),
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        })
        
        # Alert on multiple failed attempts
        recent_failures = [
            attempt for attempt in self.failed_logins[ip_address]
            if datetime.now() - attempt['timestamp'] < timedelta(minutes=15)
        ]
        
        if len(recent_failures) >= 5:
            logger.warning(f"Security Alert: Multiple failed logins from IP {ip_address}")
    
    def log_suspicious_activity(self, activity_type, details):
        """Log suspicious activities"""
        self.suspicious_activities.append({
            'type': activity_type,
            'details': details,
            'ip_address': request.remote_addr,
            'timestamp': datetime.now(),
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        })
        
        logger.warning(f"Suspicious Activity: {activity_type} | {details}")
    
    def get_security_metrics(self):
        """Get security-related metrics"""
        total_failed_logins = sum(len(attempts) for attempts in self.failed_logins.values())
        
        return {
            'total_failed_logins': total_failed_logins,
            'unique_ips_with_failures': len(self.failed_logins),
            'suspicious_activities_count': len(self.suspicious_activities),
            'recent_suspicious_activities': self.suspicious_activities[-10:]
        }

# Initialize monitoring instances
monitoring = MonitoringMiddleware()
security_monitor = SecurityMonitor()

def init_monitoring(app, db):
    """Initialize monitoring for the Flask app"""
    db_monitor = DatabaseMonitor(db)
    
    @app.before_request
    def before_request():
        g.start_time = time.time()
        monitoring.log_request(request)
    
    @app.after_request
    def after_request(response):
        duration = time.time() - g.start_time
        monitoring.log_response(response, duration)
        
        # Add monitoring headers
        response.headers['X-Response-Time'] = f"{duration:.3f}s"
        response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')
        
        return response
    
    @app.route('/api/health/metrics', methods=['GET'])
    def get_health_metrics():
        """Endpoint to get application health metrics"""
        try:
            system_metrics = monitoring.get_system_metrics()
            app_metrics = monitoring.get_app_metrics()
            db_metrics = db_monitor.get_db_metrics()
            security_metrics = security_monitor.get_security_metrics()
            
            return {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'system': system_metrics,
                'application': app_metrics,
                'database': db_metrics,
                'security': security_metrics
            }, 200
            
        except Exception as e:
            logger.error(f"Error getting health metrics: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }, 500
    
    return db_monitor

