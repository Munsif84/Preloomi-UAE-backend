from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.services.shipping_service import shipping_service
import logging

shipping_bp = Blueprint('shipping', __name__)
logger = logging.getLogger(__name__)

@shipping_bp.route('/zones', methods=['GET'])
def get_delivery_zones():
    """Get available delivery zones"""
    try:
        zones = shipping_service.get_delivery_zones()
        return jsonify({
            'success': True,
            'data': zones
        }), 200
    except Exception as e:
        logger.error(f"Error getting delivery zones: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get delivery zones'
        }), 500

@shipping_bp.route('/calculate-cost', methods=['POST'])
def calculate_shipping_cost():
    """Calculate shipping cost"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['from_emirate', 'to_emirate', 'weight']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        from_emirate = data['from_emirate']
        to_emirate = data['to_emirate']
        weight = float(data['weight'])
        dimensions = data.get('dimensions')
        service_type = data.get('service_type', 'standard')
        
        # Calculate shipping cost
        result = shipping_service.calculate_shipping_cost(
            from_emirate, to_emirate, weight, dimensions, service_type
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid weight format'
        }), 400
    except Exception as e:
        logger.error(f"Error calculating shipping cost: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to calculate shipping cost'
        }), 500

@shipping_bp.route('/options', methods=['POST'])
def get_shipping_options():
    """Get available shipping options"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['from_emirate', 'to_emirate', 'weight']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        from_emirate = data['from_emirate']
        to_emirate = data['to_emirate']
        weight = float(data['weight'])
        dimensions = data.get('dimensions')
        
        # Get shipping options
        options = shipping_service.get_shipping_options(
            from_emirate, to_emirate, weight, dimensions
        )
        
        return jsonify({
            'success': True,
            'data': {
                'options': options,
                'from_emirate': from_emirate,
                'to_emirate': to_emirate,
                'weight': weight
            }
        }), 200
        
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid weight format'
        }), 400
    except Exception as e:
        logger.error(f"Error getting shipping options: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get shipping options'
        }), 500

@shipping_bp.route('/create-shipment', methods=['POST'])
@jwt_required()
def create_shipment():
    """Create a shipment"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['order_id', 'shipping_option', 'pickup_address', 'delivery_address']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        order_id = data['order_id']
        shipping_option = data['shipping_option']
        pickup_address = data['pickup_address']
        delivery_address = data['delivery_address']
        
        # Validate addresses
        pickup_validation = shipping_service.validate_address(pickup_address)
        if not pickup_validation['valid']:
            return jsonify({
                'success': False,
                'error': f'Invalid pickup address: {pickup_validation["message"]}'
            }), 400
        
        delivery_validation = shipping_service.validate_address(delivery_address)
        if not delivery_validation['valid']:
            return jsonify({
                'success': False,
                'error': f'Invalid delivery address: {delivery_validation["message"]}'
            }), 400
        
        # Prepare order data
        order_data = {
            'order_id': order_id,
            'user_id': user_id,
            'pickup_address': pickup_validation['normalized_address'],
            'delivery_address': delivery_validation['normalized_address'],
            'items': data.get('items', []),
            'special_instructions': data.get('special_instructions', '')
        }
        
        # Create shipment
        result = shipping_service.create_shipment(order_data, shipping_option)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        logger.error(f"Error creating shipment: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create shipment'
        }), 500

@shipping_bp.route('/track/<tracking_number>', methods=['GET'])
def track_shipment(tracking_number):
    """Track a shipment"""
    try:
        provider = request.args.get('provider', 'aramex')
        
        # Track shipment
        result = shipping_service.track_shipment(tracking_number, provider)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        logger.error(f"Error tracking shipment: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to track shipment'
        }), 500

@shipping_bp.route('/validate-address', methods=['POST'])
def validate_address():
    """Validate a shipping address"""
    try:
        data = request.get_json()
        
        if 'address' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing address data'
            }), 400
        
        address = data['address']
        
        # Validate address
        result = shipping_service.validate_address(address)
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error validating address: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to validate address'
        }), 500

@shipping_bp.route('/cod-availability', methods=['POST'])
def check_cod_availability():
    """Check if Cash on Delivery is available for an emirate"""
    try:
        data = request.get_json()
        
        if 'emirate' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing emirate'
            }), 400
        
        emirate = data['emirate']
        
        # Check COD availability
        available = shipping_service.get_cod_availability(emirate)
        
        return jsonify({
            'success': True,
            'data': {
                'emirate': emirate,
                'cod_available': available,
                'message': 'COD is available' if available else 'COD is not available for this emirate'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking COD availability: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to check COD availability'
        }), 500

@shipping_bp.route('/update-status', methods=['POST'])
@jwt_required()
def update_shipment_status():
    """Update shipment status (for sellers/admin)"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['tracking_number', 'status']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        tracking_number = data['tracking_number']
        status = data['status']
        location = data.get('location', '')
        notes = data.get('notes', '')
        
        # TODO: Verify user has permission to update this shipment
        # This would involve checking if user is the seller or admin
        
        # For now, just log the status update
        logger.info(f"Shipment {tracking_number} status updated to {status} by user {user_id}")
        
        return jsonify({
            'success': True,
            'data': {
                'tracking_number': tracking_number,
                'status': status,
                'updated_by': user_id,
                'message': 'Shipment status updated successfully'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating shipment status: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update shipment status'
        }), 500

@shipping_bp.route('/delivery-confirmation', methods=['POST'])
@jwt_required()
def confirm_delivery():
    """Confirm delivery (for buyers)"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['tracking_number', 'order_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        tracking_number = data['tracking_number']
        order_id = data['order_id']
        rating = data.get('rating')  # Optional delivery rating
        feedback = data.get('feedback', '')  # Optional delivery feedback
        
        # TODO: Verify user is the buyer for this order
        # TODO: Update order status to delivered/completed
        # TODO: Trigger payment release to seller (if not COD)
        
        logger.info(f"Delivery confirmed for order {order_id}, tracking {tracking_number} by user {user_id}")
        
        return jsonify({
            'success': True,
            'data': {
                'order_id': order_id,
                'tracking_number': tracking_number,
                'confirmed_by': user_id,
                'message': 'Delivery confirmed successfully'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error confirming delivery: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to confirm delivery'
        }), 500

