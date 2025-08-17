import os
import sys
# DON\'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from src.models import db
from src.routes.user import user_bp
from src.routes.item import item_bp
from src.routes.transaction import transaction_bp
from src.routes.messaging import messaging_bp
from src.routes.payment import payment_bp
from src.routes.shipping import shipping_bp
from src.middleware.security import limiter, add_security_headers
from src.middleware.monitoring import init_monitoring
from src.middleware.caching import init_caching
from src.config.security_config import get_security_config

# Initialize Flask app
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Get security configuration
SecurityConfig = get_security_config()

# Configuration
app.config['SECRET_KEY'] = SecurityConfig.JWT_SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL') # Use DATABASE_URL from environment variable
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = SecurityConfig.JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = SecurityConfig.JWT_ACCESS_TOKEN_EXPIRES

# Initialize JWT
jwt = JWTManager(app)

# Initialize rate limiter
limiter.init_app(app)

# Enable CORS for all routes
CORS(app, 
     origins=SecurityConfig.CORS_ORIGINS, 
     methods=SecurityConfig.CORS_METHODS,
     allow_headers=SecurityConfig.CORS_HEADERS)

# Add security headers to all responses
@app.after_request
def after_request(response):
    return add_security_headers(response)

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(item_bp, url_prefix='/api')
app.register_blueprint(transaction_bp, url_prefix='/api')
app.register_blueprint(messaging_bp, url_prefix='/api')
app.register_blueprint(payment_bp, url_prefix='/api')
app.register_blueprint(shipping_bp, url_prefix='/api')

# Initialize database
db.init_app(app)

# Initialize monitoring and caching
db_monitor = init_monitoring(app, db)
init_caching(app)

with app.app_context():
    db.create_all()
    
    # Create default categories if they don\'t exist
    from src.models.item import Category
    default_categories = [
        {'name': 'Women', 'sort_order': 1},
        {'name': 'Men', 'sort_order': 2},
        {'name': 'Kids', 'sort_order': 3},
        {'name': 'Home', 'sort_order': 4},
        {'name': 'Electronics', 'sort_order': 5},
        {'name': 'Sports', 'sort_order': 6}
    ]
    
    for cat_data in default_categories:
        if not Category.query.filter_by(name=cat_data['name']).first():
            category = Category(
                name=cat_data['name'],
                sort_order=cat_data['sort_order']
            )
            db.session.add(category)
    
    # Create default UAE shipping zones
    from src.models.user import UAEShippingZone
    default_zones = [
        # Dubai zones
        {'emirate': 'Dubai', 'city': 'Dubai', 'area': 'Downtown', 'delivery_zone': 'Zone 1', 'shipping_cost_zone1': 15.00},
        {'emirate': 'Dubai', 'city': 'Dubai', 'area': 'Marina', 'delivery_zone': 'Zone 1', 'shipping_cost_zone1': 15.00},
        {'emirate': 'Dubai', 'city': 'Dubai', 'area': 'JLT', 'delivery_zone': 'Zone 1', 'shipping_cost_zone1': 15.00},
        {'emirate': 'Dubai', 'city': 'Dubai', 'area': 'Business Bay', 'delivery_zone': 'Zone 1', 'shipping_cost_zone1': 15.00},
        {'emirate': 'Dubai', 'city': 'Dubai', 'area': 'DIFC', 'delivery_zone': 'Zone 1', 'shipping_cost_zone1': 15.00},
        
        # Abu Dhabi zones
        {'emirate': 'Abu Dhabi', 'city': 'Abu Dhabi', 'area': 'Corniche', 'delivery_zone': 'Zone 2', 'shipping_cost_zone2': 20.00},
        {'emirate': 'Abu Dhabi', 'city': 'Abu Dhabi', 'area': 'Khalifa City', 'delivery_zone': 'Zone 2', 'shipping_cost_zone2': 20.00},
        
        # Sharjah zones
        {'emirate': 'Sharjah', 'city': 'Sharjah', 'area': 'City Center', 'delivery_zone': 'Zone 2', 'shipping_cost_zone2': 20.00},
        
        # Other Emirates
        {'emirate': 'Ajman', 'city': 'Ajman', 'area': 'City Center', 'delivery_zone': 'Zone 3', 'shipping_cost_zone3': 25.00},
        {'emirate': 'Ras Al Khaimah', 'city': 'Ras Al Khaimah', 'area': 'City Center', 'delivery_zone': 'Zone 3', 'shipping_cost_zone3': 25.00},
        {'emirate': 'Fujairah', 'city': 'Fujairah', 'area': 'City Center', 'delivery_zone': 'Zone 3', 'shipping_cost_zone3': 25.00},
        {'emirate': 'Umm Al Quwain', 'city': 'Umm Al Quwain', 'area': 'City Center', 'delivery_zone': 'Zone 3', 'shipping_cost_zone3': 25.00}
    ]
    
    for zone_data in default_zones:
        if not UAEShippingZone.query.filter_by(
            emirate=zone_data['emirate'], 
            city=zone_data['city'], 
            area=zone_data['area']
        ).first():
            zone = UAEShippingZone(**zone_data)
            db.session.add(zone)
    
    db.session.commit()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serve frontend files."""
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "Frontend not built yet. Please build the frontend first.", 404

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return {
        'status': 'healthy',
        'message': 'Vinted Clone API is running',
        'version': '1.0.0'
    }, 200

# This ensures the 'app' object is directly available at the module level for Gunicorn
# The 'if __name__ == "__main__":' block is removed as Gunicorn handles the application startup


