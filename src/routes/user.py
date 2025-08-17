from flask import Blueprint, jsonify, request, current_app
from flask_cors import cross_origin
from src.models.user import User, Address, UAEShippingZone, db
from werkzeug.security import check_password_hash
import jwt
from datetime import datetime, timedelta
from functools import wraps

user_bp = Blueprint('user', __name__)

def token_required(f):
    """Decorator to require JWT token for protected routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'error': 'Invalid token'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

def generate_token(user_id):
    """Generate JWT token for user."""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=7)  # Token expires in 7 days
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

# Authentication routes
@user_bp.route('/auth/register', methods=['POST'])
@cross_origin()
def register():
    """Register a new user."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if user already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already taken'}), 400
        
        # Create new user
        user = User(
            username=data['username'],
            email=data['email'],
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            phone_number=data.get('phone_number'),
            location=data.get('location')
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # Generate token
        token = generate_token(user.id)
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict(),
            'token': token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/auth/login', methods=['POST'])
@cross_origin()
def login():
    """Login user."""
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        user = User.query.filter_by(email=data['email']).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # Generate token
        token = generate_token(user.id)
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(include_sensitive=True),
            'token': token
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# User profile routes
@user_bp.route('/users/profile', methods=['GET'])
@cross_origin()
@token_required
def get_profile(current_user):
    """Get current user's profile."""
    return jsonify(current_user.to_dict(include_sensitive=True)), 200

@user_bp.route('/users/profile', methods=['PUT'])
@cross_origin()
@token_required
def update_profile(current_user):
    """Update current user's profile."""
    try:
        data = request.get_json()
        
        # Update allowed fields
        allowed_fields = ['first_name', 'last_name', 'bio', 'location', 'phone_number']
        for field in allowed_fields:
            if field in data:
                setattr(current_user, field, data[field])
        
        current_user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': current_user.to_dict(include_sensitive=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/users/<user_id>', methods=['GET'])
@cross_origin()
def get_user_public(user_id):
    """Get public user profile."""
    user = User.query.get_or_404(user_id)
    if not user.is_active:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()), 200

# Address management routes
@user_bp.route('/users/addresses', methods=['GET'])
@cross_origin()
@token_required
def get_addresses(current_user):
    """Get user's addresses."""
    addresses = Address.query.filter_by(user_id=current_user.id).all()
    return jsonify([address.to_dict() for address in addresses]), 200

@user_bp.route('/users/addresses', methods=['POST'])
@cross_origin()
@token_required
def create_address(current_user):
    """Create a new address."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['address_line1', 'city', 'postal_code', 'country']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # If this is set as default, unset other default addresses
        if data.get('is_default', False):
            Address.query.filter_by(user_id=current_user.id, is_default=True).update({'is_default': False})
        
        address = Address(
            user_id=current_user.id,
            address_line1=data['address_line1'],
            address_line2=data.get('address_line2'),
            city=data['city'],
            state_province=data.get('state_province'),
            postal_code=data['postal_code'],
            country=data['country'],
            is_default=data.get('is_default', False)
        )
        
        db.session.add(address)
        db.session.commit()
        
        return jsonify({
            'message': 'Address created successfully',
            'address': address.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/users/addresses/<address_id>', methods=['PUT'])
@cross_origin()
@token_required
def update_address(current_user, address_id):
    """Update an address."""
    try:
        address = Address.query.filter_by(id=address_id, user_id=current_user.id).first_or_404()
        data = request.get_json()
        
        # If this is set as default, unset other default addresses
        if data.get('is_default', False) and not address.is_default:
            Address.query.filter_by(user_id=current_user.id, is_default=True).update({'is_default': False})
        
        # Update allowed fields
        allowed_fields = ['address_line1', 'address_line2', 'city', 'state_province', 
                         'postal_code', 'country', 'is_default']
        for field in allowed_fields:
            if field in data:
                setattr(address, field, data[field])
        
        address.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Address updated successfully',
            'address': address.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/users/addresses/<address_id>', methods=['DELETE'])
@cross_origin()
@token_required
def delete_address(current_user, address_id):
    """Delete an address."""
    try:
        address = Address.query.filter_by(id=address_id, user_id=current_user.id).first_or_404()
        db.session.delete(address)
        db.session.commit()
        
        return jsonify({'message': 'Address deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# UAE shipping zones
@user_bp.route('/shipping/uae-zones', methods=['GET'])
@cross_origin()
def get_uae_shipping_zones():
    """Get UAE shipping zones for delivery cost calculation."""
    zones = UAEShippingZone.query.filter_by(is_active=True).all()
    return jsonify([zone.to_dict() for zone in zones]), 200

@user_bp.route('/shipping/calculate-cost', methods=['POST'])
@cross_origin()
def calculate_shipping_cost():
    """Calculate shipping cost based on delivery address."""
    try:
        data = request.get_json()
        emirate = data.get('emirate')
        city = data.get('city')
        
        if not emirate or not city:
            return jsonify({'error': 'Emirate and city are required'}), 400
        
        zone = UAEShippingZone.query.filter_by(
            emirate=emirate, 
            city=city, 
            is_active=True
        ).first()
        
        if not zone:
            # Default to Zone 3 if specific zone not found
            return jsonify({
                'delivery_zone': 'Zone 3',
                'shipping_cost': 25.00,
                'currency': 'AED',
                'standard_delivery_days': 3,
                'express_delivery_available': False,
                'cod_available': True
            }), 200
        
        return jsonify({
            'delivery_zone': zone.delivery_zone,
            'shipping_cost': float(zone.shipping_cost_zone1) if zone.delivery_zone == 'Zone 1' 
                           else float(zone.shipping_cost_zone2) if zone.delivery_zone == 'Zone 2'
                           else float(zone.shipping_cost_zone3),
            'currency': 'AED',
            'standard_delivery_days': zone.standard_delivery_days,
            'express_delivery_available': zone.express_delivery_available,
            'cod_available': zone.cod_available
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

