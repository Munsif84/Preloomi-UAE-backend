import stripe
import os
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime

# Configure Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_...')  # Use test key for development

class PaymentService:
    """Service for handling payment processing"""
    
    def __init__(self):
        self.supported_methods = ['card', 'cod', 'wallet']
        self.supported_currencies = ['AED', 'USD']
    
    def create_payment_intent(self, amount: float, currency: str = 'AED', 
                            payment_method: str = 'card', metadata: Dict = None) -> Dict[str, Any]:
        """Create a payment intent for card payments"""
        try:
            if payment_method == 'cod':
                return self._create_cod_payment(amount, currency, metadata)
            
            # Convert AED to cents (Stripe uses smallest currency unit)
            amount_cents = int(amount * 100)
            
            # Create Stripe payment intent
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                metadata=metadata or {},
                automatic_payment_methods={
                    'enabled': True,
                },
            )
            
            return {
                'success': True,
                'payment_intent_id': intent.id,
                'client_secret': intent.client_secret,
                'amount': amount,
                'currency': currency,
                'status': intent.status,
                'payment_method': payment_method
            }
            
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'general_error'
            }
    
    def _create_cod_payment(self, amount: float, currency: str, metadata: Dict = None) -> Dict[str, Any]:
        """Create a Cash on Delivery payment record"""
        return {
            'success': True,
            'payment_intent_id': f"cod_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{metadata.get('order_id', 'unknown')}",
            'client_secret': None,  # COD doesn't need client secret
            'amount': amount,
            'currency': currency,
            'status': 'requires_confirmation',  # COD requires delivery confirmation
            'payment_method': 'cod',
            'instructions': 'Payment will be collected upon delivery'
        }
    
    def confirm_payment(self, payment_intent_id: str, payment_method_id: str = None) -> Dict[str, Any]:
        """Confirm a payment intent"""
        try:
            if payment_intent_id.startswith('cod_'):
                return self._confirm_cod_payment(payment_intent_id)
            
            # Confirm Stripe payment intent
            intent = stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method=payment_method_id
            )
            
            return {
                'success': True,
                'payment_intent_id': intent.id,
                'status': intent.status,
                'amount': intent.amount / 100,  # Convert back from cents
                'currency': intent.currency.upper()
            }
            
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'general_error'
            }
    
    def _confirm_cod_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        """Confirm COD payment (when delivery is completed)"""
        return {
            'success': True,
            'payment_intent_id': payment_intent_id,
            'status': 'succeeded',
            'message': 'COD payment confirmed upon delivery'
        }
    
    def get_payment_status(self, payment_intent_id: str) -> Dict[str, Any]:
        """Get the status of a payment"""
        try:
            if payment_intent_id.startswith('cod_'):
                return {
                    'success': True,
                    'payment_intent_id': payment_intent_id,
                    'status': 'requires_confirmation',
                    'payment_method': 'cod'
                }
            
            # Get Stripe payment intent
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                'success': True,
                'payment_intent_id': intent.id,
                'status': intent.status,
                'amount': intent.amount / 100,
                'currency': intent.currency.upper(),
                'payment_method': 'card'
            }
            
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'general_error'
            }
    
    def refund_payment(self, payment_intent_id: str, amount: float = None) -> Dict[str, Any]:
        """Refund a payment"""
        try:
            if payment_intent_id.startswith('cod_'):
                return {
                    'success': False,
                    'error': 'COD payments cannot be refunded automatically',
                    'message': 'Please handle COD refund manually'
                }
            
            # Get the payment intent to find the charge
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if not intent.charges.data:
                return {
                    'success': False,
                    'error': 'No charge found for this payment intent'
                }
            
            charge_id = intent.charges.data[0].id
            refund_amount = int((amount or (intent.amount / 100)) * 100)
            
            # Create refund
            refund = stripe.Refund.create(
                charge=charge_id,
                amount=refund_amount
            )
            
            return {
                'success': True,
                'refund_id': refund.id,
                'amount': refund.amount / 100,
                'currency': refund.currency.upper(),
                'status': refund.status
            }
            
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'general_error'
            }
    
    def calculate_fees(self, amount: float, payment_method: str = 'card') -> Dict[str, Any]:
        """Calculate payment processing fees"""
        if payment_method == 'cod':
            # COD typically has a flat fee
            cod_fee = 5.0  # 5 AED COD fee
            return {
                'payment_fee': cod_fee,
                'platform_fee': amount * 0.05,  # 5% platform fee
                'total_fees': cod_fee + (amount * 0.05),
                'net_amount': amount - cod_fee - (amount * 0.05)
            }
        
        elif payment_method == 'card':
            # Stripe fees: 2.9% + 2 AED per transaction
            stripe_fee = (amount * 0.029) + 2.0
            platform_fee = amount * 0.05  # 5% platform fee
            
            return {
                'payment_fee': stripe_fee,
                'platform_fee': platform_fee,
                'total_fees': stripe_fee + platform_fee,
                'net_amount': amount - stripe_fee - platform_fee
            }
        
        else:
            return {
                'payment_fee': 0,
                'platform_fee': amount * 0.05,
                'total_fees': amount * 0.05,
                'net_amount': amount * 0.95
            }
    
    def validate_payment_method(self, payment_method: str) -> bool:
        """Validate if payment method is supported"""
        return payment_method in self.supported_methods
    
    def get_supported_payment_methods(self) -> Dict[str, Any]:
        """Get list of supported payment methods"""
        return {
            'methods': [
                {
                    'id': 'card',
                    'name': 'Credit/Debit Card',
                    'description': 'Pay securely with your credit or debit card',
                    'icon': 'credit-card',
                    'processing_time': 'Instant',
                    'fees': '2.9% + 2 AED'
                },
                {
                    'id': 'cod',
                    'name': 'Cash on Delivery',
                    'description': 'Pay with cash when your order is delivered',
                    'icon': 'banknote',
                    'processing_time': 'On delivery',
                    'fees': '5 AED'
                }
            ],
            'currencies': self.supported_currencies,
            'default_currency': 'AED'
        }

# Singleton instance
payment_service = PaymentService()

