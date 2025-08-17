from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from src.models.user import db

class Conversation(db.Model):
    __tablename__ = 'conversations'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    participant1_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    participant2_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    item_id = db.Column(db.String(36), db.ForeignKey('items.id'))  # Optional: conversation about specific item
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade='all, delete-orphan')
    participant1 = db.relationship('User', foreign_keys=[participant1_id], backref='conversations_as_participant1')
    participant2 = db.relationship('User', foreign_keys=[participant2_id], backref='conversations_as_participant2')
    item = db.relationship('Item', foreign_keys=[item_id])

    def __repr__(self):
        return f'<Conversation {self.id}>'

    def get_other_participant(self, user_id):
        """Get the other participant in the conversation."""
        if self.participant1_id == user_id:
            return self.participant2
        elif self.participant2_id == user_id:
            return self.participant1
        return None

    def to_dict(self, current_user_id=None, include_messages=False):
        """Convert conversation object to dictionary."""
        conversation_dict = {
            'id': self.id,
            'participant1_id': self.participant1_id,
            'participant2_id': self.participant2_id,
            'item_id': self.item_id,
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        # Include other participant info if current_user_id is provided
        if current_user_id:
            other_participant = self.get_other_participant(current_user_id)
            if other_participant:
                conversation_dict['other_participant'] = other_participant.to_dict()
        
        # Include item info if conversation is about a specific item
        if self.item:
            conversation_dict['item'] = self.item.to_dict(include_seller=False)
        
        # Include recent messages if requested
        if include_messages and self.messages:
            # Get last 10 messages
            recent_messages = sorted(self.messages, key=lambda x: x.sent_at, reverse=True)[:10]
            conversation_dict['recent_messages'] = [msg.to_dict() for msg in recent_messages]
            
        return conversation_dict


class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False)
    sender_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    message_text = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(50), default='text')  # text, image, offer, system
    attachment_url = db.Column(db.String(255))  # For image messages or attachments
    offer_amount = db.Column(db.Numeric(10, 2))  # For offer messages
    offer_currency = db.Column(db.String(3), default='AED')
    is_read = db.Column(db.Boolean, default=False)
    is_system_message = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id])

    def __repr__(self):
        return f'<Message {self.id}>'

    def mark_as_read(self):
        """Mark the message as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()

    def to_dict(self, include_sender=True):
        """Convert message object to dictionary."""
        message_dict = {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'sender_id': self.sender_id,
            'message_text': self.message_text,
            'message_type': self.message_type,
            'attachment_url': self.attachment_url,
            'offer_amount': float(self.offer_amount) if self.offer_amount else None,
            'offer_currency': self.offer_currency,
            'is_read': self.is_read,
            'is_system_message': self.is_system_message,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None
        }
        
        if include_sender and self.sender:
            message_dict['sender'] = self.sender.to_dict()
            
        return message_dict


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)
    # message, order, payment, shipping, system, promotion
    related_id = db.Column(db.String(36))  # ID of related object (order, message, etc.)
    is_read = db.Column(db.Boolean, default=False)
    is_push_sent = db.Column(db.Boolean, default=False)
    is_email_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref='notifications')

    def __repr__(self):
        return f'<Notification {self.title}>'

    def mark_as_read(self):
        """Mark the notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()

    def to_dict(self):
        """Convert notification object to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'notification_type': self.notification_type,
            'related_id': self.related_id,
            'is_read': self.is_read,
            'is_push_sent': self.is_push_sent,
            'is_email_sent': self.is_email_sent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None
        }

