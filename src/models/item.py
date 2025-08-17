from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from src.models.user import db

class Item(db.Model):
    __tablename__ = 'items'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='AED')
    category = db.Column(db.String(100), nullable=False)
    subcategory = db.Column(db.String(100))
    condition = db.Column(db.String(50), nullable=False)  # New, Good, Fair
    brand = db.Column(db.String(100))
    size = db.Column(db.String(50))
    color = db.Column(db.String(50))
    material = db.Column(db.String(100))
    status = db.Column(db.String(50), default='available')  # available, sold, reserved, deleted
    views_count = db.Column(db.Integer, default=0)
    likes_count = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    images = db.relationship('ItemImage', backref='item', lazy=True, cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='item', lazy=True)

    def __repr__(self):
        return f'<Item {self.title}>'

    def to_dict(self, include_seller=True):
        """Convert item object to dictionary."""
        item_dict = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'price': float(self.price) if self.price else None,
            'currency': self.currency,
            'category': self.category,
            'subcategory': self.subcategory,
            'condition': self.condition,
            'brand': self.brand,
            'size': self.size,
            'color': self.color,
            'material': self.material,
            'status': self.status,
            'views_count': self.views_count,
            'likes_count': self.likes_count,
            'is_featured': self.is_featured,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'images': [img.to_dict() for img in self.images] if self.images else []
        }
        
        if include_seller and self.seller:
            item_dict['seller'] = self.seller.to_dict()
        else:
            item_dict['seller_id'] = self.seller_id
            
        return item_dict


class ItemImage(db.Model):
    __tablename__ = 'item_images'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    item_id = db.Column(db.String(36), db.ForeignKey('items.id'), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    order_index = db.Column(db.Integer, default=0)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ItemImage {self.image_url}>'

    def to_dict(self):
        """Convert item image object to dictionary."""
        return {
            'id': self.id,
            'item_id': self.item_id,
            'image_url': self.image_url,
            'order_index': self.order_index,
            'is_primary': self.is_primary,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False, unique=True)
    parent_id = db.Column(db.String(36), db.ForeignKey('categories.id'))
    icon_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Self-referential relationship for subcategories
    subcategories = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))

    def __repr__(self):
        return f'<Category {self.name}>'

    def to_dict(self, include_subcategories=False):
        """Convert category object to dictionary."""
        category_dict = {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'icon_url': self.icon_url,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_subcategories and self.subcategories:
            category_dict['subcategories'] = [sub.to_dict() for sub in self.subcategories if sub.is_active]
            
        return category_dict

