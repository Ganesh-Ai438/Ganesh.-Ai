#!/usr/bin/env python3
"""
Ganesh AI - Cashfree Payment Integration
Real payment processing for revenue generation
"""

import os
import json
import hmac
import hashlib
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import uuid

# Cashfree imports (with fallback)
try:
    from cashfree_sdk import Cashfree
    from cashfree_sdk.models import CreateOrderRequest, CustomerDetails, OrderMeta
    CASHFREE_AVAILABLE = True
except ImportError:
    CASHFREE_AVAILABLE = False
    print("⚠️ Cashfree SDK not available. Payment features will be limited.")

from main import app, db, User, log

class CashfreePaymentSystem:
    """Complete Cashfree Payment Integration"""
    
    def __init__(self):
        # Cashfree credentials from environment
        self.app_id = os.getenv('CASHFREE_APP_ID')
        self.secret_key = os.getenv('CASHFREE_SECRET_KEY')
        self.environment = os.getenv('CASHFREE_ENVIRONMENT', 'sandbox')  # sandbox or production
        
        # API endpoints
        if self.environment == 'production':
            self.base_url = 'https://api.cashfree.com'
        else:
            self.base_url = 'https://sandbox.cashfree.com'
        
        self.is_configured = bool(self.app_id and self.secret_key)
        
        if self.is_configured and CASHFREE_AVAILABLE:
            # Initialize Cashfree SDK
            Cashfree.XClientId = self.app_id
            Cashfree.XClientSecret = self.secret_key
            Cashfree.XEnvironment = Cashfree.SANDBOX if self.environment == 'sandbox' else Cashfree.PRODUCTION
            log("payment", "INFO", f"Cashfree initialized in {self.environment} mode")
        else:
            log("payment", "WARNING", "Cashfree not properly configured")
    
    def create_payment_order(self, user_id: int, amount: float, purpose: str, 
                           return_url: str = None, notify_url: str = None) -> Dict:
        """Create a payment order with Cashfree"""
        if not self.is_configured:
            return {
                'success': False,
                'message': 'Payment system not configured',
                'demo_mode': True
            }
        
        try:
            with app.app_context():
                user = User.query.get(user_id)
                if not user:
                    return {'success': False, 'message': 'User not found'}
                
                # Generate unique order ID
                order_id = f"GANESH_{user_id}_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
                
                # Create order data
                order_data = {
                    "order_id": order_id,
                    "order_amount": amount,
                    "order_currency": "INR",
                    "customer_details": {
                        "customer_id": str(user_id),
                        "customer_name": user.username,
                        "customer_email": user.email,
                        "customer_phone": user.phone or "9999999999"
                    },
                    "order_meta": {
                        "return_url": return_url or f"{os.getenv('DOMAIN', 'http://localhost:5000')}/payment/success",
                        "notify_url": notify_url or f"{os.getenv('DOMAIN', 'http://localhost:5000')}/payment/webhook",
                        "payment_methods": "cc,dc,nb,upi,wallet"
                    },
                    "order_note": f"Payment for {purpose} - Ganesh AI"
                }
                
                # Make API request to create order
                headers = {
                    'X-Client-Id': self.app_id,
                    'X-Client-Secret': self.secret_key,
                    'Content-Type': 'application/json'
                }
                
                response = requests.post(
                    f"{self.base_url}/pg/orders",
                    headers=headers,
                    json=order_data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Store order in database
                    from main import PaymentOrder
                    payment_order = PaymentOrder(
                        user_id=user_id,
                        order_id=order_id,
                        amount=amount,
                        currency='INR',
                        purpose=purpose,
                        status='created',
                        gateway_response=json.dumps(result)
                    )
                    db.session.add(payment_order)
                    db.session.commit()
                    
                    log("payment", "INFO", f"Payment order created: {order_id} for user {user_id}")
                    
                    return {
                        'success': True,
                        'order_id': order_id,
                        'payment_session_id': result.get('payment_session_id'),
                        'payment_url': result.get('payment_link'),
                        'amount': amount,
                        'currency': 'INR'
                    }
                else:
                    error_msg = f"Cashfree API error: {response.status_code} - {response.text}"
                    log("payment", "ERROR", error_msg)
                    return {
                        'success': False,
                        'message': 'Failed to create payment order',
                        'error': error_msg
                    }
                    
        except Exception as e:
            log("payment", "ERROR", f"Payment order creation failed: {e}")
            return {
                'success': False,
                'message': 'Payment system error',
                'error': str(e)
            }
    
    def verify_payment(self, order_id: str) -> Dict:
        """Verify payment status with Cashfree"""
        if not self.is_configured:
            return {'success': False, 'message': 'Payment system not configured'}
        
        try:
            headers = {
                'X-Client-Id': self.app_id,
                'X-Client-Secret': self.secret_key,
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.base_url}/pg/orders/{order_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Update order status in database
                with app.app_context():
                    from main import PaymentOrder
                    payment_order = PaymentOrder.query.filter_by(order_id=order_id).first()
                    if payment_order:
                        payment_order.status = result.get('order_status', 'unknown').lower()
                        payment_order.gateway_response = json.dumps(result)
                        payment_order.updated_at = datetime.utcnow()
                        db.session.commit()
                
                return {
                    'success': True,
                    'order_id': order_id,
                    'status': result.get('order_status'),
                    'amount': result.get('order_amount'),
                    'payment_details': result
                }
            else:
                error_msg = f"Payment verification failed: {response.status_code} - {response.text}"
                log("payment", "ERROR", error_msg)
                return {
                    'success': False,
                    'message': 'Payment verification failed',
                    'error': error_msg
                }
                
        except Exception as e:
            log("payment", "ERROR", f"Payment verification error: {e}")
            return {
                'success': False,
                'message': 'Payment verification error',
                'error': str(e)
            }
    
    def process_webhook(self, webhook_data: Dict, signature: str) -> Dict:
        """Process Cashfree webhook notification"""
        try:
            # Verify webhook signature
            if not self.verify_webhook_signature(webhook_data, signature):
                log("payment", "ERROR", "Invalid webhook signature")
                return {'success': False, 'message': 'Invalid signature'}
            
            order_id = webhook_data.get('order_id')
            event_type = webhook_data.get('type')
            
            log("payment", "INFO", f"Webhook received: {event_type} for order {order_id}")
            
            with app.app_context():
                from main import PaymentOrder
                payment_order = PaymentOrder.query.filter_by(order_id=order_id).first()
                
                if not payment_order:
                    log("payment", "ERROR", f"Payment order not found: {order_id}")
                    return {'success': False, 'message': 'Order not found'}
                
                # Update order status
                payment_order.status = webhook_data.get('order_status', 'unknown').lower()
                payment_order.gateway_response = json.dumps(webhook_data)
                payment_order.updated_at = datetime.utcnow()
                
                # Process successful payment
                if event_type == 'PAYMENT_SUCCESS' and payment_order.status == 'paid':
                    self.process_successful_payment(payment_order, webhook_data)
                
                db.session.commit()
                
                return {'success': True, 'message': 'Webhook processed'}
                
        except Exception as e:
            log("payment", "ERROR", f"Webhook processing error: {e}")
            return {'success': False, 'message': 'Webhook processing failed'}
    
    def process_successful_payment(self, payment_order, webhook_data: Dict):
        """Process successful payment and update user account"""
        try:
            user = User.query.get(payment_order.user_id)
            if not user:
                log("payment", "ERROR", f"User not found for payment: {payment_order.user_id}")
                return
            
            amount = float(payment_order.amount)
            purpose = payment_order.purpose
            
            # Process based on payment purpose
            if purpose == 'wallet_topup':
                # Add money to wallet
                user.wallet += amount
                user.add_earnings(amount, f"Wallet top-up via Cashfree")
                log("payment", "INFO", f"Wallet topped up: ₹{amount} for user {user.username}")
                
            elif purpose == 'premium_monthly':
                # Activate monthly premium
                if user.premium_until and user.premium_until > datetime.utcnow():
                    user.premium_until += timedelta(days=30)
                else:
                    user.premium_until = datetime.utcnow() + timedelta(days=30)
                log("payment", "INFO", f"Monthly premium activated for user {user.username}")
                
            elif purpose == 'premium_yearly':
                # Activate yearly premium
                if user.premium_until and user.premium_until > datetime.utcnow():
                    user.premium_until += timedelta(days=365)
                else:
                    user.premium_until = datetime.utcnow() + timedelta(days=365)
                log("payment", "INFO", f"Yearly premium activated for user {user.username}")
            
            # Create transaction record
            from main import Transaction
            transaction = Transaction(
                user_id=user.id,
                type='credit',
                amount=amount,
                description=f"Payment received: {purpose}",
                reference=payment_order.order_id
            )
            db.session.add(transaction)
            
            # Send success notification (if email/SMS service is configured)
            self.send_payment_notification(user, amount, purpose)
            
            db.session.commit()
            
        except Exception as e:
            log("payment", "ERROR", f"Payment processing error: {e}")
    
    def verify_webhook_signature(self, webhook_data: Dict, signature: str) -> bool:
        """Verify Cashfree webhook signature"""
        try:
            # Create signature string
            signature_string = ""
            for key in sorted(webhook_data.keys()):
                signature_string += f"{key}{webhook_data[key]}"
            
            # Generate expected signature
            expected_signature = hmac.new(
                self.secret_key.encode('utf-8'),
                signature_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            log("payment", "ERROR", f"Signature verification error: {e}")
            return False
    
    def send_payment_notification(self, user: User, amount: float, purpose: str):
        """Send payment success notification to user"""
        try:
            # This would integrate with email/SMS service
            # For now, just log the notification
            log("payment", "INFO", f"Payment notification: ₹{amount} {purpose} for {user.username}")
            
            # TODO: Integrate with email service (SendGrid, AWS SES, etc.)
            # TODO: Integrate with SMS service (Twilio, AWS SNS, etc.)
            
        except Exception as e:
            log("payment", "ERROR", f"Notification sending error: {e}")
    
    def create_withdrawal_request(self, user_id: int, amount: float, 
                                bank_details: Dict) -> Dict:
        """Create withdrawal request (payout)"""
        if not self.is_configured:
            return {
                'success': False,
                'message': 'Payment system not configured',
                'demo_mode': True
            }
        
        try:
            with app.app_context():
                user = User.query.get(user_id)
                if not user:
                    return {'success': False, 'message': 'User not found'}
                
                if user.wallet < amount:
                    return {'success': False, 'message': 'Insufficient balance'}
                
                if amount < 100:
                    return {'success': False, 'message': 'Minimum withdrawal amount is ₹100'}
                
                # Generate unique transfer ID
                transfer_id = f"WITHDRAW_{user_id}_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
                
                # Create payout request
                payout_data = {
                    "transferId": transfer_id,
                    "amount": amount,
                    "phone": user.phone or "9999999999",
                    "bankAccount": bank_details.get('account_number'),
                    "ifsc": bank_details.get('ifsc_code'),
                    "email": user.email,
                    "name": bank_details.get('account_holder_name', user.username)
                }
                
                headers = {
                    'X-Client-Id': self.app_id,
                    'X-Client-Secret': self.secret_key,
                    'Content-Type': 'application/json'
                }
                
                response = requests.post(
                    f"{self.base_url}/payout/v1/directTransfer",
                    headers=headers,
                    json=payout_data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Deduct from wallet
                    user.wallet -= amount
                    
                    # Create withdrawal record
                    from main import WithdrawalRequest
                    withdrawal = WithdrawalRequest(
                        user_id=user_id,
                        amount=amount,
                        status='processing',
                        transfer_id=transfer_id,
                        bank_details=json.dumps(bank_details),
                        gateway_response=json.dumps(result)
                    )
                    db.session.add(withdrawal)
                    db.session.commit()
                    
                    log("payment", "INFO", f"Withdrawal request created: {transfer_id} for user {user_id}")
                    
                    return {
                        'success': True,
                        'transfer_id': transfer_id,
                        'amount': amount,
                        'status': 'processing',
                        'message': 'Withdrawal request submitted successfully'
                    }
                else:
                    error_msg = f"Payout API error: {response.status_code} - {response.text}"
                    log("payment", "ERROR", error_msg)
                    return {
                        'success': False,
                        'message': 'Failed to process withdrawal',
                        'error': error_msg
                    }
                    
        except Exception as e:
            log("payment", "ERROR", f"Withdrawal request failed: {e}")
            return {
                'success': False,
                'message': 'Withdrawal system error',
                'error': str(e)
            }
    
    def get_payment_methods(self) -> List[Dict]:
        """Get available payment methods"""
        return [
            {
                'id': 'upi',
                'name': 'UPI',
                'description': 'Pay using UPI apps like GPay, PhonePe, Paytm',
                'icon': '📱'
            },
            {
                'id': 'netbanking',
                'name': 'Net Banking',
                'description': 'Pay using your bank account',
                'icon': '🏦'
            },
            {
                'id': 'card',
                'name': 'Credit/Debit Card',
                'description': 'Pay using Visa, Mastercard, RuPay',
                'icon': '💳'
            },
            {
                'id': 'wallet',
                'name': 'Digital Wallets',
                'description': 'Pay using Paytm, PhonePe, Amazon Pay',
                'icon': '💰'
            }
        ]
    
    def get_transaction_history(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get user's transaction history"""
        try:
            with app.app_context():
                from main import Transaction, PaymentOrder, WithdrawalRequest
                
                # Get payment orders
                payments = PaymentOrder.query.filter_by(user_id=user_id)\
                    .order_by(PaymentOrder.created_at.desc()).limit(limit).all()
                
                # Get withdrawals
                withdrawals = WithdrawalRequest.query.filter_by(user_id=user_id)\
                    .order_by(WithdrawalRequest.created_at.desc()).limit(limit).all()
                
                # Get general transactions
                transactions = Transaction.query.filter_by(user_id=user_id)\
                    .order_by(Transaction.created_at.desc()).limit(limit).all()
                
                history = []
                
                # Add payments
                for payment in payments:
                    history.append({
                        'id': payment.order_id,
                        'type': 'payment',
                        'amount': float(payment.amount),
                        'status': payment.status,
                        'purpose': payment.purpose,
                        'date': payment.created_at.isoformat(),
                        'description': f"Payment: {payment.purpose}"
                    })
                
                # Add withdrawals
                for withdrawal in withdrawals:
                    history.append({
                        'id': withdrawal.transfer_id or f"W{withdrawal.id}",
                        'type': 'withdrawal',
                        'amount': float(withdrawal.amount),
                        'status': withdrawal.status,
                        'purpose': 'withdrawal',
                        'date': withdrawal.created_at.isoformat(),
                        'description': f"Withdrawal: ₹{withdrawal.amount}"
                    })
                
                # Add transactions
                for txn in transactions:
                    history.append({
                        'id': txn.reference or f"T{txn.id}",
                        'type': txn.type,
                        'amount': float(txn.amount),
                        'status': 'completed',
                        'purpose': 'earning',
                        'date': txn.created_at.isoformat(),
                        'description': txn.description
                    })
                
                # Sort by date (newest first)
                history.sort(key=lambda x: x['date'], reverse=True)
                
                return history[:limit]
                
        except Exception as e:
            log("payment", "ERROR", f"Transaction history error: {e}")
            return []

# Global payment system instance
cashfree_system = CashfreePaymentSystem()

# Helper functions for main.py integration
def create_payment_order(user_id: int, amount: float, purpose: str) -> Dict:
    """Create payment order"""
    return cashfree_system.create_payment_order(user_id, amount, purpose)

def verify_payment(order_id: str) -> Dict:
    """Verify payment status"""
    return cashfree_system.verify_payment(order_id)

def process_webhook(webhook_data: Dict, signature: str) -> Dict:
    """Process payment webhook"""
    return cashfree_system.process_webhook(webhook_data, signature)

def create_withdrawal(user_id: int, amount: float, bank_details: Dict) -> Dict:
    """Create withdrawal request"""
    return cashfree_system.create_withdrawal_request(user_id, amount, bank_details)

def get_payment_methods() -> List[Dict]:
    """Get available payment methods"""
    return cashfree_system.get_payment_methods()

def get_transaction_history(user_id: int, limit: int = 50) -> List[Dict]:
    """Get transaction history"""
    return cashfree_system.get_transaction_history(user_id, limit)