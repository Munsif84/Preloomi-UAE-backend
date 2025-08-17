from flask import Blueprint, jsonify, request, current_app
from flask_cors import cross_origin
from src.models.transaction import Order, Transaction, Shipment, db
from src.models.item import Item
from src.models.user import Address
from src.routes.user import token_required
from datetime import datetime
from decimal import Decimal

transaction_bp = Blueprint('transaction', __name__)

# Order management
@transaction_bp.route('/orders', methods=['POST'])
@cross_origin()
@token_required
def create_order(current_user):
    """Create a new order."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['item_id', 'shipping_address_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Get item and validate
        item = Item.query.get_or_404(data['item_id'])
        if item.status != 'available':
            return jsonify({'error': 'Item is not available'}), 400
        
        if item.seller_id == current_user.id:
            return jsonify({'error': 'Cannot buy your own item'}), 400
        
        # Get shipping address and validate
        shipping_address = Address.query.filter_by(
            id=data['shipping_address_id'], 
            user_id=current_user.id
        ).first_or_404()
        
        # Calculate pricing
        item_price = Decimal(str(item.price))
        shipping_cost = Decimal(str(data.get('shipping_cost', 15.00)))  # Default UAE shipping
        buyer_protection_fee = item_price * Decimal('0.05') + Decimal('2.50')  # 5% + 2.50 AED
        total_price = item_price + shipping_cost + buyer_protection_fee
        
        # Create order
        order = Order(
            buyer_id=current_user.id,
            seller_id=item.seller_id,
            item_id=item.id,
            shipping_address_id=shipping_address.id,
            item_price=item_price,
            shipping_cost=shipping_cost,
            buyer_protection_fee=buyer_protection_fee,
            total_price=total_price,
            currency=item.currency,
            order_status='pending',
            payment_status='pending'
        )
        
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Reserve the item
        item.status = 'reserved'
        item.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Order created successfully',
            'order': order.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/orders/<order_id>', methods=['GET'])
@cross_origin()
@token_required
def get_order(current_user, order_id):
    """Get order details."""
    try:
        order = Order.query.filter(
            Order.id == order_id,
            (Order.buyer_id == current_user.id) | (Order.seller_id == current_user.id)
        ).first_or_404()
        
        return jsonify(order.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/orders', methods=['GET'])
@cross_origin()
@token_required
def get_user_orders(current_user):
    """Get user's orders (as buyer or seller)."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        role = request.args.get('role', 'all')  # all, buyer, seller
        status = request.args.get('status')
        
        query = Order.query
        
        if role == 'buyer':
            query = query.filter_by(buyer_id=current_user.id)
        elif role == 'seller':
            query = query.filter_by(seller_id=current_user.id)
        else:
            query = query.filter(
                (Order.buyer_id == current_user.id) | (Order.seller_id == current_user.id)
            )
        
        if status:
            query = query.filter_by(order_status=status)
        
        orders = query.order_by(Order.created_at.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'orders': [order.to_dict() for order in orders.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': orders.total,
                'pages': orders.pages,
                'has_next': orders.has_next,
                'has_prev': orders.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/orders/<order_id>/confirm-payment', methods=['POST'])
@cross_origin()
@token_required
def confirm_payment(current_user, order_id):
    """Confirm payment for an order."""
    try:
        order = Order.query.filter_by(id=order_id, buyer_id=current_user.id).first_or_404()
        
        if order.payment_status != 'pending':
            return jsonify({'error': 'Payment already processed'}), 400
        
        data = request.get_json()
        payment_method = data.get('payment_method', 'cod')
        
        # Create transaction record
        transaction = Transaction(
            order_id=order.id,
            payment_gateway_id=data.get('payment_gateway_id'),
            amount=order.total_price,
            currency=order.currency,
            transaction_type='payment',
            status='success' if payment_method == 'cod' else 'pending',
            payment_method=payment_method
        )
        
        db.session.add(transaction)
        
        # Update order status
        if payment_method == 'cod':
            order.payment_status = 'paid'
            order.order_status = 'confirmed'
        else:
            order.payment_status = 'pending'
            order.order_status = 'pending'
        
        order.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Payment confirmed successfully',
            'order': order.to_dict(),
            'transaction': transaction.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/orders/<order_id>/ship', methods=['POST'])
@cross_origin()
@token_required
def ship_order(current_user, order_id):
    """Mark order as shipped (seller action)."""
    try:
        order = Order.query.filter_by(id=order_id, seller_id=current_user.id).first_or_404()
        
        if order.order_status not in ['confirmed', 'paid']:
            return jsonify({'error': 'Order cannot be shipped in current status'}), 400
        
        data = request.get_json()
        
        # Create shipment record
        shipment = Shipment(
            order_id=order.id,
            carrier=data.get('carrier', 'Aramex'),
            tracking_number=data.get('tracking_number'),
            shipping_cost=order.shipping_cost,
            currency=order.currency,
            status='picked_up',
            label_url=data.get('label_url')
        )
        
        db.session.add(shipment)
        
        # Update order status
        order.order_status = 'shipped'
        order.shipped_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        
        # Update item status
        item = Item.query.get(order.item_id)
        item.status = 'sold'
        item.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Order shipped successfully',
            'order': order.to_dict(),
            'shipment': shipment.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/orders/<order_id>/confirm-delivery', methods=['POST'])
@cross_origin()
@token_required
def confirm_delivery(current_user, order_id):
    """Confirm delivery (buyer action)."""
    try:
        order = Order.query.filter_by(id=order_id, buyer_id=current_user.id).first_or_404()
        
        if order.order_status != 'shipped':
            return jsonify({'error': 'Order is not in shipped status'}), 400
        
        # Update order status
        order.order_status = 'delivered'
        order.delivered_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        
        # Update shipment status
        shipment = Shipment.query.filter_by(order_id=order.id).first()
        if shipment:
            shipment.status = 'delivered'
            shipment.actual_delivery = datetime.utcnow()
            shipment.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Delivery confirmed successfully',
            'order': order.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/orders/<order_id>/complete', methods=['POST'])
@cross_origin()
@token_required
def complete_order(current_user, order_id):
    """Complete order and release payment to seller (buyer action)."""
    try:
        order = Order.query.filter_by(id=order_id, buyer_id=current_user.id).first_or_404()
        
        if order.order_status != 'delivered':
            return jsonify({'error': 'Order must be delivered before completion'}), 400
        
        # Create payout transaction for seller
        payout_amount = order.item_price + order.shipping_cost  # Seller gets item price + shipping
        payout_transaction = Transaction(
            order_id=order.id,
            amount=payout_amount,
            currency=order.currency,
            transaction_type='payout',
            status='success',
            payment_method='wallet'
        )
        
        db.session.add(payout_transaction)
        
        # Update order status
        order.order_status = 'completed'
        order.completed_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Order completed successfully',
            'order': order.to_dict(),
            'payout': payout_transaction.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/orders/<order_id>/cancel', methods=['POST'])
@cross_origin()
@token_required
def cancel_order(current_user, order_id):
    """Cancel an order."""
    try:
        order = Order.query.filter(
            Order.id == order_id,
            (Order.buyer_id == current_user.id) | (Order.seller_id == current_user.id)
        ).first_or_404()
        
        if order.order_status not in ['pending', 'confirmed']:
            return jsonify({'error': 'Order cannot be cancelled in current status'}), 400
        
        data = request.get_json()
        reason = data.get('reason', 'User requested cancellation')
        
        # Update order status
        order.order_status = 'cancelled'
        order.updated_at = datetime.utcnow()
        
        # Release item back to available
        item = Item.query.get(order.item_id)
        item.status = 'available'
        item.updated_at = datetime.utcnow()
        
        # Create refund transaction if payment was made
        if order.payment_status == 'paid':
            refund_transaction = Transaction(
                order_id=order.id,
                amount=order.total_price,
                currency=order.currency,
                transaction_type='refund',
                status='success',
                payment_method=order.transactions[0].payment_method if order.transactions else 'cod'
            )
            db.session.add(refund_transaction)
            order.payment_status = 'refunded'
        
        db.session.commit()
        
        return jsonify({
            'message': 'Order cancelled successfully',
            'order': order.to_dict(),
            'reason': reason
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Transaction history
@transaction_bp.route('/transactions', methods=['GET'])
@cross_origin()
@token_required
def get_user_transactions(current_user):
    """Get user's transaction history."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        transaction_type = request.args.get('type')
        
        # Get orders for the user
        user_orders = Order.query.filter(
            (Order.buyer_id == current_user.id) | (Order.seller_id == current_user.id)
        ).subquery()
        
        query = Transaction.query.join(user_orders, Transaction.order_id == user_orders.c.id)
        
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        
        transactions = query.order_by(Transaction.created_at.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'transactions': [transaction.to_dict() for transaction in transactions.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': transactions.total,
                'pages': transactions.pages,
                'has_next': transactions.has_next,
                'has_prev': transactions.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

