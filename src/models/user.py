from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    profile_picture_url = db.Column(db.String(255))
    bio = db.Column(db.Text)
    location = db.Column(db.String(100))
    phone_number = db.Column(db.String(20))
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('Item', backref='seller', lazy=True, foreign_keys='Item.seller_id')
    addresses = db.relationship('Address', backref='user', lazy=True)
    orders_as_buyer = db.relationship('Order', backref='buyer', lazy=True, foreign_keys='Order.buyer_id')
    orders_as_seller = db.relationship('Order', backref='seller', lazy=True, foreign_keys='Order.seller_id')

    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the user's password."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self, include_sensitive=False):
        """Convert user object to dictionary."""
        user_dict = {
            'id': self.id,
            'username': self.username,
            'email': self.email if include_sensitive else None,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'profile_picture_url': self.profile_picture_url,
            'bio': self.bio,
            'location': self.location,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        # Remove None values
        return {k: v for k, v in user_dict.items() if v is not None}


class Address(db.Model):
    __tablename__ = 'addresses'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    address_line1 = db.Column(db.String(255), nullable=False)
    address_line2 = db.Column(db.String(255))
    city = db.Column(db.String(100), nullable=False)
    state_province = db.Column(db.String(100))
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Address {self.address_line1}, {self.city}>'

    def to_dict(self):
        """Convert address object to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'address_line1': self.address_line1,
            'address_line2': self.address_line2,
            'city': self.city,
            'state_province': self.state_province,
            'postal_code': self.postal_code,
            'country': self.country,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }



class UAEShippingZone(db.Model):
    __tablename__ = 'uae_shipping_zones'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    emirate = db.Column(db.String(50), nullable=False)  # Dubai, Abu Dhabi, Sharjah, etc.
    city = db.Column(db.String(100), nullable=False)
    area = db.Column(db.String(100))
    postal_code = db.Column(db.String(10))
    delivery_zone = db.Column(db.String(20), nullable=False)  # Zone 1, Zone 2, Zone 3
    standard_delivery_days = db.Column(db.Integer, default=2)
    express_delivery_available = db.Column(db.Boolean, default=True)
    cod_available = db.Column(db.Boolean, default=True)
    shipping_cost_zone1 = db.Column(db.Numeric(5, 2), default=15.00)  # AED
    shipping_cost_zone2 = db.Column(db.Numeric(5, 2), default=20.00)  # AED
    shipping_cost_zone3 = db.Column(db.Numeric(5, 2), default=25.00)  # AED
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<UAEShippingZone {self.emirate} - {self.city}>'

    def to_dict(self):
        """Convert UAE shipping zone object to dictionary."""
        return {
            'id': self.id,
            'emirate': self.emirate,
            'city': self.city,
            'area': self.area,
            'postal_code': self.postal_code,
            'delivery_zone': self.delivery_zone,
            'standard_delivery_days': self.standard_delivery_days,
            'express_delivery_available': self.express_delivery_available,
            'cod_available': self.cod_available,
            'shipping_cost_zone1': float(self.shipping_cost_zone1) if self.shipping_cost_zone1 else None,
            'shipping_cost_zone2': float(self.shipping_cost_zone2) if self.shipping_cost_zone2 else None,
            'shipping_cost_zone3': float(self.shipping_cost_zone3) if self.shipping_cost_zone3 else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

