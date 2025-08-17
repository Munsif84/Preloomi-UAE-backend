import os
from datetime import timedelta

class SecurityConfig:
    """Security configuration settings"""
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'vinted_clone_jwt_secret_2024_uae')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ALGORITHM = 'HS256'
    
    # Password Configuration
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 128
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGITS = True
    PASSWORD_REQUIRE_SPECIAL_CHARS = True
    
    # Rate Limiting Configuration
    RATE_LIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/1')
    DEFAULT_RATE_LIMIT = "1000 per hour"
    LOGIN_RATE_LIMIT = "10 per minute"
    REGISTER_RATE_LIMIT = "5 per minute"
    API_RATE_LIMIT = "100 per minute"
    
    # Session Configuration
    SESSION_TIMEOUT = timedelta(hours=24)
    MAX_FAILED_LOGIN_ATTEMPTS = 5
    ACCOUNT_LOCKOUT_DURATION = timedelta(minutes=15)
    
    # File Upload Security
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    UPLOAD_FOLDER = 'uploads'
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    CORS_HEADERS = ['Content-Type', 'Authorization', 'X-Requested-With']
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }
    
    # Encryption Configuration
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'default_encryption_key_change_in_production')
    
    # API Security
    API_KEY_LENGTH = 32
    API_KEY_EXPIRY = timedelta(days=365)
    
    # Database Security
    DB_CONNECTION_POOL_SIZE = 10
    DB_CONNECTION_TIMEOUT = 30
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = 'logs/security.log'
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # Monitoring Configuration
    MONITOR_FAILED_LOGINS = True
    MONITOR_SUSPICIOUS_ACTIVITIES = True
    ALERT_THRESHOLD_FAILED_LOGINS = 10
    ALERT_THRESHOLD_ERROR_RATE = 5.0  # 5%
    
    # UAE Specific Security
    UAE_PHONE_VALIDATION = True
    REQUIRE_PHONE_VERIFICATION = True
    REQUIRE_EMAIL_VERIFICATION = True
    
    # Payment Security
    PAYMENT_WEBHOOK_SECRET = os.getenv('PAYMENT_WEBHOOK_SECRET', 'webhook_secret_change_in_production')
    PAYMENT_ENCRYPTION_ENABLED = True
    
    # Data Protection (GDPR/UAE Data Protection Law)
    DATA_RETENTION_PERIOD = timedelta(days=2555)  # 7 years
    ANONYMIZE_DATA_AFTER_DELETION = True
    REQUIRE_CONSENT_FOR_DATA_PROCESSING = True
    
    @classmethod
    def get_security_config(cls):
        """Get all security configuration as a dictionary"""
        return {
            'jwt': {
                'secret_key': cls.JWT_SECRET_KEY,
                'access_token_expires': cls.JWT_ACCESS_TOKEN_EXPIRES.total_seconds(),
                'refresh_token_expires': cls.JWT_REFRESH_TOKEN_EXPIRES.total_seconds(),
                'algorithm': cls.JWT_ALGORITHM
            },
            'password': {
                'min_length': cls.PASSWORD_MIN_LENGTH,
                'max_length': cls.PASSWORD_MAX_LENGTH,
                'require_uppercase': cls.PASSWORD_REQUIRE_UPPERCASE,
                'require_lowercase': cls.PASSWORD_REQUIRE_LOWERCASE,
                'require_digits': cls.PASSWORD_REQUIRE_DIGITS,
                'require_special_chars': cls.PASSWORD_REQUIRE_SPECIAL_CHARS
            },
            'rate_limiting': {
                'storage_url': cls.RATE_LIMIT_STORAGE_URL,
                'default_limit': cls.DEFAULT_RATE_LIMIT,
                'login_limit': cls.LOGIN_RATE_LIMIT,
                'register_limit': cls.REGISTER_RATE_LIMIT,
                'api_limit': cls.API_RATE_LIMIT
            },
            'file_upload': {
                'max_size': cls.MAX_FILE_SIZE,
                'allowed_extensions': list(cls.ALLOWED_IMAGE_EXTENSIONS),
                'upload_folder': cls.UPLOAD_FOLDER
            },
            'monitoring': {
                'failed_logins': cls.MONITOR_FAILED_LOGINS,
                'suspicious_activities': cls.MONITOR_SUSPICIOUS_ACTIVITIES,
                'alert_threshold_failed_logins': cls.ALERT_THRESHOLD_FAILED_LOGINS,
                'alert_threshold_error_rate': cls.ALERT_THRESHOLD_ERROR_RATE
            }
        }
    
    @classmethod
    def validate_config(cls):
        """Validate security configuration"""
        errors = []
        
        # Check required environment variables
        required_env_vars = ['JWT_SECRET_KEY', 'ENCRYPTION_KEY', 'PAYMENT_WEBHOOK_SECRET']
        for var in required_env_vars:
            if not os.getenv(var) or os.getenv(var) == f'default_{var.lower()}_change_in_production':
                errors.append(f"Environment variable {var} must be set in production")
        
        # Validate password requirements
        if cls.PASSWORD_MIN_LENGTH < 8:
            errors.append("Password minimum length should be at least 8 characters")
        
        # Validate file upload settings
        if cls.MAX_FILE_SIZE > 50 * 1024 * 1024:  # 50MB
            errors.append("Maximum file size should not exceed 50MB")
        
        return errors

class ProductionSecurityConfig(SecurityConfig):
    """Production-specific security configuration"""
    
    # Stricter settings for production
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)  # Shorter token expiry
    LOGIN_RATE_LIMIT = "5 per minute"  # Stricter rate limiting
    REGISTER_RATE_LIMIT = "3 per minute"
    API_RATE_LIMIT = "60 per minute"
    
    # Enhanced monitoring
    ALERT_THRESHOLD_FAILED_LOGINS = 5
    ALERT_THRESHOLD_ERROR_RATE = 2.0  # 2%
    
    # Stricter CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'https://yourdomain.com').split(',')

class DevelopmentSecurityConfig(SecurityConfig):
    """Development-specific security configuration"""
    
    # More relaxed settings for development
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=1)  # Longer token expiry
    LOGIN_RATE_LIMIT = "20 per minute"  # More relaxed rate limiting
    REGISTER_RATE_LIMIT = "10 per minute"
    API_RATE_LIMIT = "200 per minute"
    
    # Less strict monitoring
    ALERT_THRESHOLD_FAILED_LOGINS = 20
    ALERT_THRESHOLD_ERROR_RATE = 10.0  # 10%

def get_security_config():
    """Get appropriate security configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    
    if env == 'production':
        return ProductionSecurityConfig
    else:
        return DevelopmentSecurityConfig

