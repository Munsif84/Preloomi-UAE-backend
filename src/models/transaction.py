from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from src.models.user import db

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    buyer_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    seller_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    item_id = db.Column(db.String(36), db.ForeignKey('items.id'), nullable=False)
    shipping_address_id = db.Column(db.String(36), db.ForeignKey('addresses.id'), nullable=False)
    
    # Pricing
    item_price = db.Column(db.Numeric(10, 2), nullable=False)
    shipping_cost = db.Column(db.Numeric(10, 2), default=0)
    buyer_protection_fee = db.Column(db.Numeric(10, 2), default=0)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='AED')
    
    # Status and tracking
    order_status = db.Column(db.String(50), nullable=False, default='pending')
    # pending, confirmed, shipped, delivered, completed, cancelled, disputed
    payment_status = db.Column(db.String(50), nullable=False, default='pending')
    # pending, paid, failed, refunded, partially_refunded
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    shipped_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='order', lazy=True)
    shipments = db.relationship('Shipment', backref='order', lazy=True)
    shipping_address = db.relationship('Address', foreign_keys=[shipping_address_id])

    def __repr__(self):
        return f'<Order {self.id}>'

    def to_dict(self, include_details=True):
        """Convert order object to dictionary."""
        order_dict = {
            'id': self.id,
            'buyer_id': self.buyer_id,
            'seller_id': self.seller_id,
            'item_id': self.item_id,
            'shipping_address_id': self.shipping_address_id,
            'item_price': float(self.item_price) if self.item_price else None,
            'shipping_cost': float(self.shipping_cost) if self.shipping_cost else None,
            'buyer_protection_fee': float(self.buyer_protection_fee) if self.buyer_protection_fee else None,
            'total_price': float(self.total_price) if self.total_price else None,
            'currency': self.currency,
            'order_status': self.order_status,
            'payment_status': self.payment_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'shipped_at': self.shipped_at.isoformat() if self.shipped_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
        
        if include_details:
            if self.item:
                order_dict['item'] = self.item.to_dict(include_seller=False)
            if self.buyer:
                order_dict['buyer'] = self.buyer.to_dict()
            if self.seller:
                order_dict['seller'] = self.seller.to_dict()
            if self.shipping_address:
                order_dict['shipping_address'] = self.shipping_address.to_dict()
                
        return order_dict


class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = db.Column(db.String(36), db.ForeignKey('orders.id'), nullable=False)
    payment_gateway_id = db.Column(db.String(255))  # External payment gateway transaction ID
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='AED')
    transaction_type = db.Column(db.String(50), nullable=False)
    # payment, refund, payout, fee, chargeback
    status = db.Column(db.String(50), nullable=False, default='pending')
    # pending, success, failed, cancelled
    payment_method = db.Column(db.String(50))  # card, cod, wallet, bank_transfer
    gateway_response = db.Column(db.Text)  # JSON response from payment gateway
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Transaction {self.id}>'

    def to_dict(self):
        """Convert transaction object to dictionary."""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'payment_gateway_id': self.payment_gateway_id,
            'amount': float(self.amount) if self.amount else None,
            'currency': self.currency,
            'transaction_type': self.transaction_type,
            'status': self.status,
            'payment_method': self.payment_method,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Shipment(db.Model):
    __tablename__ = 'shipments'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = db.Column(db.String(36), db.ForeignKey('orders.id'), nullable=False)
    carrier = db.Column(db.String(100))  # Aramex, DHL, FedEx, etc.
    tracking_number = db.Column(db.String(255), unique=True)
    shipping_cost = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='AED')
    status = db.Column(db.String(50), nullable=False, default='pending')
    # pending, label_created, picked_up, in_transit, out_for_delivery, delivered, failed, returned
    label_url = db.Column(db.String(255))
    estimated_delivery = db.Column(db.DateTime)
    actual_delivery = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Shipment {self.tracking_number}>'

    def to_dict(self):
        """Convert shipment object to dictionary."""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'carrier': self.carrier,
            'tracking_number': self.tracking_number,
            'shipping_cost': float(self.shipping_cost) if self.shipping_cost else None,
            'currency': self.currency,
            'status': self.status,
            'label_url': self.label_url,
            'estimated_delivery': self.estimated_delivery.isoformat() if self.estimated_delivery else None,
            'actual_delivery': self.actual_delivery.isoformat() if self.actual_delivery else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

