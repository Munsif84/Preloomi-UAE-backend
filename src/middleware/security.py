from functools import wraps
from flask import request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import re
import bleach
import logging
from datetime import datetime, timedelta
import hashlib
import hmac
import os

logger = logging.getLogger(__name__)

# Rate limiter configuration
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per hour", "100 per minute"]
)

class SecurityMiddleware:
    """Security middleware for input validation, sanitization, and protection"""
    
    def __init__(self):
        self.blocked_ips = set()
        self.failed_attempts = {}
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
    
    def validate_email(self, email):
        """Validate email format"""
        if not email or len(email) > 254:
            return False
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email) is not None
    
    def validate_phone(self, phone):
        """Validate UAE phone number format"""
        if not phone:
            return False
        
        # Remove all non-digit characters
        phone_digits = re.sub(r'\D', '', phone)
        
        # UAE phone patterns
        uae_patterns = [
            r'^971[0-9]{8,9}$',  # +971 format
            r'^05[0-9]{8}$',     # Local mobile format
            r'^04[0-9]{7}$',     # Dubai landline
            r'^02[0-9]{7}$',     # Abu Dhabi landline
            r'^06[0-9]{7}$',     # Sharjah landline
            r'^07[0-9]{7}$',     # Other emirates landline
        ]
        
        return any(re.match(pattern, phone_digits) for pattern in uae_patterns)
    
    def validate_password(self, password):
        """Validate password strength"""
        if not password or len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if len(password) > 128:
            return False, "Password must be less than 128 characters"
        
        # Check for at least one uppercase, lowercase, digit, and special character
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        return True, "Password is valid"
    
    def sanitize_input(self, text, max_length=None):
        """Sanitize text input to prevent XSS"""
        if not text:
            return text
        
        # Remove HTML tags and potentially dangerous content
        cleaned = bleach.clean(text, tags=[], attributes={}, strip=True)
        
        # Limit length if specified
        if max_length and len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
        
        return cleaned.strip()
    
    def validate_uae_address(self, address):
        """Validate UAE address format"""
        required_fields = ['street', 'city', 'emirate']
        errors = []
        
        for field in required_fields:
            if not address.get(field):
                errors.append(f"{field} is required")
        
        # Validate emirate
        valid_emirates = [
            'Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 
            'Ras Al Khaimah', 'Fujairah', 'Umm Al Quwain'
        ]
        
        if address.get('emirate') and address['emirate'] not in valid_emirates:
            errors.append("Invalid emirate")
        
        # Validate postal code (UAE postal codes are typically 5 digits)
        if address.get('postal_code'):
            if not re.match(r'^\d{5}$', address['postal_code']):
                errors.append("Postal code must be 5 digits")
        
        return len(errors) == 0, errors
    
    def validate_price(self, price):
        """Validate price format and range"""
        try:
            price_float = float(price)
            if price_float < 0:
                return False, "Price cannot be negative"
            if price_float > 100000:  # 100,000 AED max
                return False, "Price cannot exceed 100,000 AED"
            return True, "Price is valid"
        except (ValueError, TypeError):
            return False, "Invalid price format"
    
    def check_rate_limit(self, ip_address, endpoint):
        """Check if IP has exceeded rate limits"""
        if ip_address in self.blocked_ips:
            return False, "IP address is blocked"
        
        # Check failed login attempts
        if endpoint in ['/api/login', '/api/register']:
            attempts = self.failed_attempts.get(ip_address, [])
            recent_attempts = [
                attempt for attempt in attempts 
                if datetime.now() - attempt < self.lockout_duration
            ]
            
            if len(recent_attempts) >= self.max_failed_attempts:
                return False, f"Too many failed attempts. Try again in {self.lockout_duration.total_seconds()/60:.0f} minutes"
        
        return True, "Rate limit OK"
    
    def record_failed_attempt(self, ip_address):
        """Record a failed login attempt"""
        if ip_address not in self.failed_attempts:
            self.failed_attempts[ip_address] = []
        
        self.failed_attempts[ip_address].append(datetime.now())
        
        # Clean old attempts
        self.failed_attempts[ip_address] = [
            attempt for attempt in self.failed_attempts[ip_address]
            if datetime.now() - attempt < self.lockout_duration
        ]
    
    def validate_file_upload(self, file):
        """Validate file upload"""
        if not file:
            return False, "No file provided"
        
        # Check file size (max 10MB)
        if hasattr(file, 'content_length') and file.content_length > 10 * 1024 * 1024:
            return False, "File size cannot exceed 10MB"
        
        # Check file extension
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        filename = file.filename.lower() if file.filename else ''
        
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            return False, "Only image files (JPG, PNG, GIF, WebP) are allowed"
        
        return True, "File is valid"
    
    def generate_csrf_token(self, user_id):
        """Generate CSRF token for user"""
        secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
        timestamp = str(int(datetime.now().timestamp()))
        
        message = f"{user_id}:{timestamp}"
        signature = hmac.new(
            secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{message}:{signature}"
    
    def validate_csrf_token(self, token, user_id):
        """Validate CSRF token"""
        try:
            parts = token.split(':')
            if len(parts) != 3:
                return False
            
            token_user_id, timestamp, signature = parts
            
            # Check if user ID matches
            if token_user_id != str(user_id):
                return False
            
            # Check if token is not too old (1 hour max)
            token_time = datetime.fromtimestamp(int(timestamp))
            if datetime.now() - token_time > timedelta(hours=1):
                return False
            
            # Verify signature
            secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
            message = f"{token_user_id}:{timestamp}"
            expected_signature = hmac.new(
                secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except (ValueError, TypeError):
            return False

# Security decorators
def require_rate_limit(limit="100 per minute"):
    """Decorator to apply rate limiting to endpoints"""
    def decorator(f):
        @wraps(f)
        @limiter.limit(limit)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_json_input(required_fields=None, optional_fields=None):
    """Decorator to validate JSON input"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Content-Type must be application/json'
                }), 400
            
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Invalid JSON data'
                }), 400
            
            # Check required fields
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return jsonify({
                        'success': False,
                        'error': f'Missing required fields: {", ".join(missing_fields)}'
                    }), 400
            
            # Sanitize all string inputs
            security = SecurityMiddleware()
            for key, value in data.items():
                if isinstance(value, str):
                    data[key] = security.sanitize_input(value, max_length=1000)
            
            # Store sanitized data in g for use in the route
            g.json_data = data
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_security_event(event_type, details=None):
    """Log security-related events"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip_address = get_remote_address()
            user_agent = request.headers.get('User-Agent', 'Unknown')
            
            logger.info(f"Security Event: {event_type} | IP: {ip_address} | User-Agent: {user_agent} | Details: {details}")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Security headers middleware
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# Initialize security middleware instance
security_middleware = SecurityMiddleware()

