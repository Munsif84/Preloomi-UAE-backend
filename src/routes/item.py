from flask import Blueprint, jsonify, request, current_app
from flask_cors import cross_origin
from src.models.item import Item, ItemImage, Category, db
from src.models.user import User
from src.routes.user import token_required
from datetime import datetime
from sqlalchemy import or_, and_

item_bp = Blueprint('item', __name__)

# Item listing routes
@item_bp.route('/items', methods=['GET'])
@cross_origin()
def get_items():
    """Get items with search and filtering."""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        search_query = request.args.get('q', '').strip()
        category = request.args.get('category')
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        condition = request.args.get('condition')
        size = request.args.get('size')
        brand = request.args.get('brand')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Build query
        query = Item.query.filter_by(status='available')
        
        # Search in title and description
        if search_query:
            query = query.filter(
                or_(
                    Item.title.ilike(f'%{search_query}%'),
                    Item.description.ilike(f'%{search_query}%'),
                    Item.brand.ilike(f'%{search_query}%')
                )
            )
        
        # Apply filters
        if category:
            query = query.filter(Item.category == category)
        if min_price is not None:
            query = query.filter(Item.price >= min_price)
        if max_price is not None:
            query = query.filter(Item.price <= max_price)
        if condition:
            query = query.filter(Item.condition == condition)
        if size:
            query = query.filter(Item.size == size)
        if brand:
            query = query.filter(Item.brand.ilike(f'%{brand}%'))
        
        # Apply sorting
        if sort_by == 'price':
            if sort_order == 'asc':
                query = query.order_by(Item.price.asc())
            else:
                query = query.order_by(Item.price.desc())
        elif sort_by == 'created_at':
            if sort_order == 'asc':
                query = query.order_by(Item.created_at.asc())
            else:
                query = query.order_by(Item.created_at.desc())
        elif sort_by == 'views':
            query = query.order_by(Item.views_count.desc())
        elif sort_by == 'likes':
            query = query.order_by(Item.likes_count.desc())
        
        # Paginate results
        items = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'items': [item.to_dict() for item in items.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': items.total,
                'pages': items.pages,
                'has_next': items.has_next,
                'has_prev': items.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@item_bp.route('/items/<item_id>', methods=['GET'])
@cross_origin()
def get_item(item_id):
    """Get item details."""
    try:
        item = Item.query.get_or_404(item_id)
        
        # Increment view count
        item.views_count += 1
        db.session.commit()
        
        return jsonify(item.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@item_bp.route('/items', methods=['POST'])
@cross_origin()
@token_required
def create_item(current_user):
    """Create a new item listing."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'price', 'category', 'condition']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Create item
        item = Item(
            seller_id=current_user.id,
            title=data['title'],
            description=data.get('description'),
            price=data['price'],
            currency=data.get('currency', 'AED'),
            category=data['category'],
            subcategory=data.get('subcategory'),
            condition=data['condition'],
            brand=data.get('brand'),
            size=data.get('size'),
            color=data.get('color'),
            material=data.get('material')
        )
        
        db.session.add(item)
        db.session.flush()  # Get the item ID
        
        # Add images if provided
        images = data.get('images', [])
        for i, image_url in enumerate(images):
            item_image = ItemImage(
                item_id=item.id,
                image_url=image_url,
                order_index=i,
                is_primary=(i == 0)
            )
            db.session.add(item_image)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Item created successfully',
            'item': item.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@item_bp.route('/items/<item_id>', methods=['PUT'])
@cross_origin()
@token_required
def update_item(current_user, item_id):
    """Update an item listing."""
    try:
        item = Item.query.filter_by(id=item_id, seller_id=current_user.id).first_or_404()
        data = request.get_json()
        
        # Update allowed fields
        allowed_fields = ['title', 'description', 'price', 'category', 'subcategory',
                         'condition', 'brand', 'size', 'color', 'material', 'status']
        for field in allowed_fields:
            if field in data:
                setattr(item, field, data[field])
        
        item.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Item updated successfully',
            'item': item.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@item_bp.route('/items/<item_id>', methods=['DELETE'])
@cross_origin()
@token_required
def delete_item(current_user, item_id):
    """Delete an item listing."""
    try:
        item = Item.query.filter_by(id=item_id, seller_id=current_user.id).first_or_404()
        
        # Soft delete by changing status
        item.status = 'deleted'
        item.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'Item deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# User's items
@item_bp.route('/users/items', methods=['GET'])
@cross_origin()
@token_required
def get_user_items(current_user):
    """Get current user's items."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status = request.args.get('status', 'available')
        
        query = Item.query.filter_by(seller_id=current_user.id)
        
        if status != 'all':
            query = query.filter_by(status=status)
        
        items = query.order_by(Item.created_at.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'items': [item.to_dict(include_seller=False) for item in items.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': items.total,
                'pages': items.pages,
                'has_next': items.has_next,
                'has_prev': items.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@item_bp.route('/users/<user_id>/items', methods=['GET'])
@cross_origin()
def get_user_public_items(user_id):
    """Get public user's items."""
    try:
        user = User.query.get_or_404(user_id)
        if not user.is_active:
            return jsonify({'error': 'User not found'}), 404
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        items = Item.query.filter_by(
            seller_id=user_id, 
            status='available'
        ).order_by(Item.created_at.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'items': [item.to_dict(include_seller=False) for item in items.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': items.total,
                'pages': items.pages,
                'has_next': items.has_next,
                'has_prev': items.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Categories
@item_bp.route('/categories', methods=['GET'])
@cross_origin()
def get_categories():
    """Get all categories."""
    try:
        categories = Category.query.filter_by(is_active=True, parent_id=None).order_by(Category.sort_order).all()
        return jsonify([category.to_dict(include_subcategories=True) for category in categories]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Featured items
@item_bp.route('/items/featured', methods=['GET'])
@cross_origin()
def get_featured_items():
    """Get featured items."""
    try:
        limit = min(request.args.get('limit', 10, type=int), 50)
        
        items = Item.query.filter_by(
            status='available', 
            is_featured=True
        ).order_by(Item.created_at.desc()).limit(limit).all()
        
        return jsonify([item.to_dict() for item in items]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Item statistics
@item_bp.route('/items/<item_id>/stats', methods=['GET'])
@cross_origin()
@token_required
def get_item_stats(current_user, item_id):
    """Get item statistics (for item owner)."""
    try:
        item = Item.query.filter_by(id=item_id, seller_id=current_user.id).first_or_404()
        
        stats = {
            'views_count': item.views_count,
            'likes_count': item.likes_count,
            'created_at': item.created_at.isoformat(),
            'days_listed': (datetime.utcnow() - item.created_at).days
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

