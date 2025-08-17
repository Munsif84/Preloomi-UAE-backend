from flask import Blueprint, jsonify, request, current_app
from flask_cors import cross_origin
from src.models.messaging import Conversation, Message, Notification, db
from src.models.user import User
from src.models.item import Item
from src.routes.user import token_required
from datetime import datetime
from sqlalchemy import or_, and_

messaging_bp = Blueprint('messaging', __name__)

# Conversation management
@messaging_bp.route('/conversations', methods=['GET'])
@cross_origin()
@token_required
def get_conversations(current_user):
    """Get user's conversations."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        conversations = Conversation.query.filter(
            or_(
                Conversation.participant1_id == current_user.id,
                Conversation.participant2_id == current_user.id
            ),
            Conversation.is_active == True
        ).order_by(Conversation.last_message_at.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'conversations': [conv.to_dict(current_user_id=current_user.id) for conv in conversations.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': conversations.total,
                'pages': conversations.pages,
                'has_next': conversations.has_next,
                'has_prev': conversations.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@messaging_bp.route('/conversations', methods=['POST'])
@cross_origin()
@token_required
def create_conversation(current_user):
    """Start a new conversation."""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('recipient_id'):
            return jsonify({'error': 'recipient_id is required'}), 400
        
        recipient_id = data['recipient_id']
        item_id = data.get('item_id')
        
        # Validate recipient exists
        recipient = User.query.get_or_404(recipient_id)
        if not recipient.is_active:
            return jsonify({'error': 'Recipient not found'}), 404
        
        if recipient_id == current_user.id:
            return jsonify({'error': 'Cannot start conversation with yourself'}), 400
        
        # Check if conversation already exists
        existing_conversation = Conversation.query.filter(
            or_(
                and_(
                    Conversation.participant1_id == current_user.id,
                    Conversation.participant2_id == recipient_id
                ),
                and_(
                    Conversation.participant1_id == recipient_id,
                    Conversation.participant2_id == current_user.id
                )
            ),
            Conversation.item_id == item_id if item_id else Conversation.item_id.is_(None)
        ).first()
        
        if existing_conversation:
            return jsonify({
                'message': 'Conversation already exists',
                'conversation': existing_conversation.to_dict(current_user_id=current_user.id)
            }), 200
        
        # Validate item if provided
        if item_id:
            item = Item.query.get_or_404(item_id)
            if item.status not in ['available', 'reserved']:
                return jsonify({'error': 'Item is not available for discussion'}), 400
        
        # Create new conversation
        conversation = Conversation(
            participant1_id=current_user.id,
            participant2_id=recipient_id,
            item_id=item_id
        )
        
        db.session.add(conversation)
        db.session.commit()
        
        return jsonify({
            'message': 'Conversation created successfully',
            'conversation': conversation.to_dict(current_user_id=current_user.id)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@messaging_bp.route('/conversations/<conversation_id>', methods=['GET'])
@cross_origin()
@token_required
def get_conversation(current_user, conversation_id):
    """Get conversation details."""
    try:
        conversation = Conversation.query.filter(
            Conversation.id == conversation_id,
            or_(
                Conversation.participant1_id == current_user.id,
                Conversation.participant2_id == current_user.id
            )
        ).first_or_404()
        
        return jsonify(conversation.to_dict(
            current_user_id=current_user.id, 
            include_messages=True
        )), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Message management
@messaging_bp.route('/conversations/<conversation_id>/messages', methods=['GET'])
@cross_origin()
@token_required
def get_messages(current_user, conversation_id):
    """Get messages in a conversation."""
    try:
        # Verify user is part of conversation
        conversation = Conversation.query.filter(
            Conversation.id == conversation_id,
            or_(
                Conversation.participant1_id == current_user.id,
                Conversation.participant2_id == current_user.id
            )
        ).first_or_404()
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        
        messages = Message.query.filter_by(
            conversation_id=conversation_id
        ).order_by(Message.sent_at.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # Mark messages as read for current user
        unread_messages = Message.query.filter(
            Message.conversation_id == conversation_id,
            Message.sender_id != current_user.id,
            Message.is_read == False
        ).all()
        
        for message in unread_messages:
            message.mark_as_read()
        
        db.session.commit()
        
        return jsonify({
            'messages': [message.to_dict() for message in reversed(messages.items)],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': messages.total,
                'pages': messages.pages,
                'has_next': messages.has_next,
                'has_prev': messages.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@messaging_bp.route('/conversations/<conversation_id>/messages', methods=['POST'])
@cross_origin()
@token_required
def send_message(current_user, conversation_id):
    """Send a message in a conversation."""
    try:
        # Verify user is part of conversation
        conversation = Conversation.query.filter(
            Conversation.id == conversation_id,
            or_(
                Conversation.participant1_id == current_user.id,
                Conversation.participant2_id == current_user.id
            )
        ).first_or_404()
        
        data = request.get_json()
        
        # Validate message content
        message_text = data.get('message_text', '').strip()
        message_type = data.get('message_type', 'text')
        
        if not message_text and message_type == 'text':
            return jsonify({'error': 'Message text is required'}), 400
        
        # Create message
        message = Message(
            conversation_id=conversation_id,
            sender_id=current_user.id,
            message_text=message_text,
            message_type=message_type,
            attachment_url=data.get('attachment_url'),
            offer_amount=data.get('offer_amount'),
            offer_currency=data.get('offer_currency', 'AED')
        )
        
        db.session.add(message)
        
        # Update conversation last message time
        conversation.last_message_at = datetime.utcnow()
        conversation.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Create notification for recipient
        recipient = conversation.get_other_participant(current_user.id)
        if recipient:
            notification = Notification(
                user_id=recipient.id,
                title='New Message',
                message=f'{current_user.username} sent you a message',
                notification_type='message',
                related_id=message.id
            )
            db.session.add(notification)
            db.session.commit()
        
        return jsonify({
            'message': 'Message sent successfully',
            'message_data': message.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@messaging_bp.route('/conversations/<conversation_id>/messages/<message_id>/read', methods=['POST'])
@cross_origin()
@token_required
def mark_message_read(current_user, conversation_id, message_id):
    """Mark a message as read."""
    try:
        # Verify user is part of conversation
        conversation = Conversation.query.filter(
            Conversation.id == conversation_id,
            or_(
                Conversation.participant1_id == current_user.id,
                Conversation.participant2_id == current_user.id
            )
        ).first_or_404()
        
        message = Message.query.filter_by(
            id=message_id,
            conversation_id=conversation_id
        ).first_or_404()
        
        # Only allow marking messages from other users as read
        if message.sender_id != current_user.id:
            message.mark_as_read()
            db.session.commit()
        
        return jsonify({'message': 'Message marked as read'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Offer management
@messaging_bp.route('/conversations/<conversation_id>/offers', methods=['POST'])
@cross_origin()
@token_required
def send_offer(current_user, conversation_id):
    """Send a price offer in a conversation."""
    try:
        # Verify user is part of conversation
        conversation = Conversation.query.filter(
            Conversation.id == conversation_id,
            or_(
                Conversation.participant1_id == current_user.id,
                Conversation.participant2_id == current_user.id
            )
        ).first_or_404()
        
        data = request.get_json()
        
        # Validate offer amount
        offer_amount = data.get('offer_amount')
        if not offer_amount or offer_amount <= 0:
            return jsonify({'error': 'Valid offer amount is required'}), 400
        
        # Create offer message
        offer_text = f"I'd like to offer {offer_amount} AED for this item."
        message = Message(
            conversation_id=conversation_id,
            sender_id=current_user.id,
            message_text=offer_text,
            message_type='offer',
            offer_amount=offer_amount,
            offer_currency=data.get('offer_currency', 'AED')
        )
        
        db.session.add(message)
        
        # Update conversation last message time
        conversation.last_message_at = datetime.utcnow()
        conversation.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Create notification for recipient
        recipient = conversation.get_other_participant(current_user.id)
        if recipient:
            notification = Notification(
                user_id=recipient.id,
                title='New Offer',
                message=f'{current_user.username} made an offer of {offer_amount} AED',
                notification_type='message',
                related_id=message.id
            )
            db.session.add(notification)
            db.session.commit()
        
        return jsonify({
            'message': 'Offer sent successfully',
            'offer': message.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Notifications
@messaging_bp.route('/notifications', methods=['GET'])
@cross_origin()
@token_required
def get_notifications(current_user):
    """Get user's notifications."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        query = Notification.query.filter_by(user_id=current_user.id)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        notifications = query.order_by(Notification.created_at.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'notifications': [notification.to_dict() for notification in notifications.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': notifications.total,
                'pages': notifications.pages,
                'has_next': notifications.has_next,
                'has_prev': notifications.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@messaging_bp.route('/notifications/<notification_id>/read', methods=['POST'])
@cross_origin()
@token_required
def mark_notification_read(current_user, notification_id):
    """Mark a notification as read."""
    try:
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first_or_404()
        
        notification.mark_as_read()
        db.session.commit()
        
        return jsonify({'message': 'Notification marked as read'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@messaging_bp.route('/notifications/mark-all-read', methods=['POST'])
@cross_origin()
@token_required
def mark_all_notifications_read(current_user):
    """Mark all notifications as read."""
    try:
        Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).update({
            'is_read': True,
            'read_at': datetime.utcnow()
        })
        
        db.session.commit()
        
        return jsonify({'message': 'All notifications marked as read'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Unread counts
@messaging_bp.route('/unread-counts', methods=['GET'])
@cross_origin()
@token_required
def get_unread_counts(current_user):
    """Get unread message and notification counts."""
    try:
        # Count unread messages
        unread_messages = Message.query.join(Conversation).filter(
            or_(
                Conversation.participant1_id == current_user.id,
                Conversation.participant2_id == current_user.id
            ),
            Message.sender_id != current_user.id,
            Message.is_read == False
        ).count()
        
        # Count unread notifications
        unread_notifications = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).count()
        
        return jsonify({
            'unread_messages': unread_messages,
            'unread_notifications': unread_notifications,
            'total_unread': unread_messages + unread_notifications
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

