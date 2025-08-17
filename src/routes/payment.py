from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.services.payment_service import payment_service
from src.models.transaction import Order
from src.models.user import User
from src.models.item import Item
import logging

payment_bp = Blueprint('payment', __name__)
logger = logging.getLogger(__name__)

@payment_bp.route('/payment-methods', methods=['GET'])
def get_payment_methods():
    """Get supported payment methods"""
    try:
        methods = payment_service.get_supported_payment_methods()
        return jsonify({
            'success': True,
            'data': methods
        }), 200
    except Exception as e:
        logger.error(f"Error getting payment methods: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get payment methods'
        }), 500

@payment_bp.route('/create-payment-intent', methods=['POST'])
@jwt_required()
def create_payment_intent():
    """Create a payment intent for an order"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['order_id', 'payment_method']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        order_id = data['order_id']
        payment_method = data['payment_method']
        
        # Validate payment method
        if not payment_service.validate_payment_method(payment_method):
            return jsonify({
                'success': False,
                'error': 'Invalid payment method'
            }), 400
        
        # Get order details (mock implementation)
        # In a real app, you'd fetch from database
        order = {
            'id': order_id,
            'buyer_id': user_id,
            'total_amount': data.get('amount', 100.0),  # Default for testing
            'currency': 'AED',
            'status': 'pending'
        }
        
        # Create payment intent
        result = payment_service.create_payment_intent(
            amount=order['total_amount'],
            currency=order['currency'],
            payment_method=payment_method,
            metadata={
                'order_id': order_id,
                'user_id': user_id
            }
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
            
    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create payment intent'
        }), 500

@payment_bp.route('/confirm-payment', methods=['POST'])
@jwt_required()
def confirm_payment():
    """Confirm a payment"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        if 'payment_intent_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing payment_intent_id'
            }), 400
        
        payment_intent_id = data['payment_intent_id']
        payment_method_id = data.get('payment_method_id')
        
        # Confirm payment
        result = payment_service.confirm_payment(payment_intent_id, payment_method_id)
        
        if result['success']:
            # Update order status (mock implementation)
            # In a real app, you'd update the database
            logger.info(f"Payment confirmed for intent {payment_intent_id}")
            
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
        logger.error(f"Error confirming payment: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to confirm payment'
        }), 500

@payment_bp.route('/payment-status/<payment_intent_id>', methods=['GET'])
@jwt_required()
def get_payment_status(payment_intent_id):
    """Get payment status"""
    try:
        result = payment_service.get_payment_status(payment_intent_id)
        
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
        logger.error(f"Error getting payment status: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get payment status'
        }), 500

@payment_bp.route('/refund', methods=['POST'])
@jwt_required()
def refund_payment():
    """Refund a payment"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        if 'payment_intent_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing payment_intent_id'
            }), 400
        
        payment_intent_id = data['payment_intent_id']
        amount = data.get('amount')  # Optional partial refund
        
        # TODO: Verify user has permission to refund this payment
        # This would involve checking if user is the seller or admin
        
        # Process refund
        result = payment_service.refund_payment(payment_intent_id, amount)
        
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
        logger.error(f"Error processing refund: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to process refund'
        }), 500

@payment_bp.route('/calculate-fees', methods=['POST'])
def calculate_payment_fees():
    """Calculate payment processing fees"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'amount' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing amount'
            }), 400
        
        amount = float(data['amount'])
        payment_method = data.get('payment_method', 'card')
        
        # Calculate fees
        fees = payment_service.calculate_fees(amount, payment_method)
        
        return jsonify({
            'success': True,
            'data': fees
        }), 200
        
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid amount format'
        }), 400
    except Exception as e:
        logger.error(f"Error calculating fees: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to calculate fees'
        }), 500

@payment_bp.route('/webhook', methods=['POST'])
def payment_webhook():
    """Handle payment provider webhooks"""
    try:
        # This would handle webhooks from Stripe, PayTabs, etc.
        # For now, just log the webhook data
        data = request.get_json()
        headers = dict(request.headers)
        
        logger.info(f"Received payment webhook: {data}")
        
        # TODO: Verify webhook signature
        # TODO: Process webhook events (payment succeeded, failed, etc.)
        
        return jsonify({
            'success': True,
            'message': 'Webhook received'
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to process webhook'
        }), 500

@payment_bp.route('/cod/confirm', methods=['POST'])
@jwt_required()
def confirm_cod_payment():
    """Confirm Cash on Delivery payment (called when delivery is completed)"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['order_id', 'payment_intent_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        order_id = data['order_id']
        payment_intent_id = data['payment_intent_id']
        
        # TODO: Verify user has permission to confirm this COD payment
        # This would typically be done by delivery personnel or system
        
        # Confirm COD payment
        result = payment_service.confirm_payment(payment_intent_id)
        
        if result['success']:
            # Update order status to completed
            logger.info(f"COD payment confirmed for order {order_id}")
            
            return jsonify({
                'success': True,
                'data': result,
                'message': 'COD payment confirmed successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        logger.error(f"Error confirming COD payment: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to confirm COD payment'
        }), 500

