"""
🤖 Ganesh A.I. - World's Most Advanced Money-Making AI Bot 💰
==============================================================
🚀 Features:
- 💬 ChatGPT-like Modern Interface
- 🧠 Multiple AI Models (GPT-4, Claude, Gemini, Llama)
- 💰 Advanced Monetization System
- 📱 Telegram Bot Integration
- 👨‍💼 Admin Panel with Analytics
- 💳 Multiple Payment Gateways
- 🎯 Visit-based Earnings
- 🔗 Referral System
- 📊 Real-time Analytics
"""

import os
import sys
import json
import time
import uuid
import base64
import logging
import traceback
import sqlite3
import threading
import asyncio
import random
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from urllib.parse import quote, unquote

import requests
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    print("⚠️ httpx not available. Some features may be limited.")
    HTTPX_AVAILABLE = False
    httpx = None
from functools import wraps

from flask import (
    Flask, request, jsonify, render_template, render_template_string,
    session, redirect, url_for, flash, send_from_directory, make_response
)
from flask_sqlalchemy import SQLAlchemy

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

from dotenv import load_dotenv
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    SCHEDULER_AVAILABLE = True
except ImportError:
    print("⚠️ APScheduler not available. Scheduled tasks will be disabled.")
    SCHEDULER_AVAILABLE = False
    BackgroundScheduler = None

# Telegram Bot imports (optional for production)
try:
    from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
    TELEGRAM_AVAILABLE = True
except ImportError:
    print("⚠️ Telegram bot dependencies not available. Running in web-only mode.")
    TELEGRAM_AVAILABLE = False
    # Define dummy classes to prevent errors
    class Update: pass
    class Bot: pass
    class InlineKeyboardButton: pass
    class InlineKeyboardMarkup: pass
    class Application: pass
    class CommandHandler: pass
    class MessageHandler: pass
    class filters: pass
    class ContextTypes: pass
    class CallbackQueryHandler: pass

# =========================
# ENVIRONMENT & CONFIG
# =========================

load_dotenv(".env")

# App Configuration
APP_NAME = os.getenv("APP_NAME", "Ganesh A.I.")
DOMAIN = os.getenv("DOMAIN", "https://brand.page/Ganeshagamingworld")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Admin Configuration
ADMIN_USER = os.getenv("ADMIN_USER", "Admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "12345")
ADMIN_ID = os.getenv("ADMIN_ID", "6646320334")

# Database Configuration
DB_URL = os.getenv("DB_URL", "sqlite:///data.db")
SQLITE_PATH = os.getenv("SQLITE_PATH", "app.db")

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "60"))

HF_API_URL = os.getenv("HUGGINGFACE_API_URL")
HF_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")

# Telegram Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_POLLING = os.getenv("TELEGRAM_POLLING", "true").lower() == "true"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Payment Gateway Configuration
CASHFREE_CLIENT_ID = os.getenv("CASHFREE_CLIENT_ID")
CASHFREE_CLIENT_SECRET = os.getenv("CASHFREE_CLIENT_SECRET")
CASHFREE_WEBHOOK_SECRET = os.getenv("CASHFREE_WEBHOOK_SECRET")

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")

# Business Configuration
BUSINESS_EMAIL = os.getenv("BUSINESS_EMAIL", "ru387653@gmail.com")
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "Artificial intelligence bot pvt Ltd")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@amanjee7568")
UPI_ID = os.getenv("UPI_ID", "9234906001@ptyes")

# 💰 MONETIZATION CONFIGURATION 💰
ENABLE_SEARCH = os.getenv("ENABLE_SEARCH", "1") == "1"
SHOW_TOOLS = os.getenv("SHOW_TOOLS", "1") == "1"

# Visit-based Earnings (per visit)
VISIT_PAY_RATE = float(os.getenv("VISIT_PAY_RATE", "0.01"))  # ₹0.01 per visit
CHAT_PAY_RATE = float(os.getenv("CHAT_PAY_RATE", "0.05"))   # ₹0.05 per chat
REFERRAL_BONUS = float(os.getenv("REFERRAL_BONUS", "10.0")) # ₹10 per referral

# Premium Plans
PREMIUM_MONTHLY = float(os.getenv("PREMIUM_MONTHLY", "99.0"))   # ₹99/month
PREMIUM_YEARLY = float(os.getenv("PREMIUM_YEARLY", "999.0"))    # ₹999/year

# AI Model Pricing (per request)
GPT4_COST = float(os.getenv("GPT4_COST", "2.0"))      # ₹2 per request
CLAUDE_COST = float(os.getenv("CLAUDE_COST", "1.5"))   # ₹1.5 per request
GEMINI_COST = float(os.getenv("GEMINI_COST", "1.0"))   # ₹1 per request
FREE_COST = float(os.getenv("FREE_COST", "0.1"))       # ₹0.1 per request

# Revenue Sharing
ADMIN_SHARE = float(os.getenv("ADMIN_SHARE", "0.7"))    # 70% to admin
USER_SHARE = float(os.getenv("USER_SHARE", "0.3"))      # 30% to user

# Security
FLASK_SECRET = os.getenv("FLASK_SECRET", "da1d476a2031fd15c3e16d5d6e9576d2")
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "1a16bb0b-4204-4ef2-8a14-fb0b50396ef8")

# =========================
# LOGGING SETUP
# =========================

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(APP_NAME)

def log(section: str, level: str, message: str, extra: Dict = None):
    """Enhanced logging function"""
    log_data = {
        "section": section,
        "msg": message,
        "extra": extra or {},
        "time": datetime.utcnow().isoformat()
    }
    
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.log(log_level, json.dumps(log_data))

# =========================
# FLASK APP SETUP
# =========================

app = Flask(__name__)
app.secret_key = FLASK_SECRET
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Database setup
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# =========================
# DATABASE MODELS
# =========================

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    wallet = db.Column(db.Float, default=0.0)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    telegram_id = db.Column(db.String(50), unique=True, nullable=True)
    
    # 💰 Monetization Fields
    total_earned = db.Column(db.Float, default=0.0)      # Total earnings
    visits_count = db.Column(db.Integer, default=0)       # Visit count
    chats_count = db.Column(db.Integer, default=0)        # Chat count
    referrals_count = db.Column(db.Integer, default=0)    # Referral count
    referral_code = db.Column(db.String(20), unique=True) # Unique referral code
    referred_by = db.Column(db.String(20), nullable=True) # Who referred this user
    premium_until = db.Column(db.DateTime, nullable=True) # Premium subscription end
    last_visit = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_premium(self):
        """Check if user has active premium subscription"""
        return self.premium_until and self.premium_until > datetime.utcnow()
    
    def generate_referral_code(self):
        """Generate unique referral code"""
        if not self.referral_code:
            self.referral_code = f"GANESH{self.id:04d}{random.randint(100, 999)}"
    
    def add_earnings(self, amount, description=""):
        """Add earnings to user wallet"""
        self.wallet += amount
        self.total_earned += amount
        
        # Create transaction record
        transaction = Transaction(
            user_id=self.id,
            amount=amount,
            transaction_type='credit',
            status='completed',
            description=description
        )
        db.session.add(transaction)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'wallet': self.wallet,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
            'total_earned': self.total_earned,
            'visits_count': self.visits_count,
            'chats_count': self.chats_count,
            'referrals_count': self.referrals_count,
            'referral_code': self.referral_code,
            'is_premium': self.is_premium()
        }

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # credit, debit
    payment_method = db.Column(db.String(50), nullable=True)
    payment_id = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=True)

class APIUsage(db.Model):
    __tablename__ = 'api_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    telegram_id = db.Column(db.String(50), nullable=True)
    api_type = db.Column(db.String(50), nullable=False)  # gpt4, claude, gemini, free
    model_name = db.Column(db.String(100), nullable=True)
    tokens_used = db.Column(db.Integer, default=0)
    cost = db.Column(db.Float, default=0.0)
    earnings_generated = db.Column(db.Float, default=0.0)  # Revenue from this request
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    request_data = db.Column(db.Text, nullable=True)
    response_data = db.Column(db.Text, nullable=True)

class Visit(db.Model):
    __tablename__ = 'visits'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    page = db.Column(db.String(200), nullable=True)
    referrer = db.Column(db.String(500), nullable=True)
    earnings_generated = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Referral(db.Model):
    __tablename__ = 'referrals'
    
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    referred_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    referral_code = db.Column(db.String(20), nullable=False)
    bonus_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='active')  # active, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PaymentOrder(db.Model):
    """Cashfree Payment Orders"""
    __tablename__ = 'payment_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_id = db.Column(db.String(100), unique=True, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='INR')
    purpose = db.Column(db.String(100), nullable=False)  # wallet_topup, premium_monthly, etc.
    status = db.Column(db.String(20), default='created')  # created, paid, failed, cancelled
    payment_session_id = db.Column(db.String(200), nullable=True)
    gateway_response = db.Column(db.Text, nullable=True)  # JSON response from Cashfree
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='payment_orders')

class WithdrawalRequest(db.Model):
    """User Withdrawal Requests"""
    __tablename__ = 'withdrawal_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    transfer_id = db.Column(db.String(100), unique=True, nullable=True)
    bank_details = db.Column(db.Text, nullable=False)  # JSON with bank account details
    gateway_response = db.Column(db.Text, nullable=True)  # JSON response from Cashfree
    admin_notes = db.Column(db.Text, nullable=True)
    processed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='withdrawal_requests')

# =========================
# DATABASE INITIALIZATION
# =========================

def init_db():
    """Initialize database with tables and admin user"""
    try:
        with app.app_context():
            db.create_all()
            
            # Create admin user if not exists
            admin_user = User.query.filter_by(username=ADMIN_USER).first()
            if not admin_user:
                admin_user = User(
                    username=ADMIN_USER,
                    email=BUSINESS_EMAIL,
                    role='admin',
                    wallet=1000.0  # Give admin some initial credits
                )
                admin_user.set_password(ADMIN_PASS)
                db.session.add(admin_user)
                db.session.commit()
                log("database", "INFO", f"Admin user created: {ADMIN_USER}")
            
        log("database", "INFO", "Database initialized successfully")
    except Exception as e:
        log("database", "ERROR", f"Database initialization failed: {e}")
        raise

# =========================
# AUTHENTICATION DECORATORS
# =========================

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return wrapper

# =========================
# 🧠 ADVANCED AI SYSTEM 🧠
# =========================

class AIModelManager:
    """Advanced AI Model Manager with multiple providers"""
    
    def __init__(self):
        self.models = {
            'gpt4': {
                'name': 'GPT-4 Turbo',
                'cost': GPT4_COST,
                'provider': 'openai',
                'model_id': 'gpt-4-turbo-preview',
                'description': '🚀 Most Advanced AI - Best for complex tasks'
            },
            'gpt3.5': {
                'name': 'GPT-3.5 Turbo',
                'cost': CLAUDE_COST,
                'provider': 'openai', 
                'model_id': 'gpt-3.5-turbo',
                'description': '⚡ Fast & Smart - Great for general tasks'
            },
            'claude': {
                'name': 'Claude 3 Sonnet',
                'cost': CLAUDE_COST,
                'provider': 'anthropic',
                'model_id': 'claude-3-sonnet-20240229',
                'description': '🎯 Precise & Analytical - Perfect for reasoning'
            },
            'gemini': {
                'name': 'Gemini Pro',
                'cost': GEMINI_COST,
                'provider': 'google',
                'model_id': 'gemini-pro',
                'description': '🌟 Google\'s Best - Excellent for creativity'
            },
            'free': {
                'name': 'Ganesh AI Free',
                'cost': FREE_COST,
                'provider': 'huggingface',
                'model_id': 'microsoft/DialoGPT-large',
                'description': '💝 Free Model - Basic conversations'
            }
        }
    
    def get_available_models(self, user=None):
        """Get available models based on user subscription"""
        available = []
        for key, model in self.models.items():
            if user and user.is_premium():
                available.append({**model, 'key': key, 'available': True})
            elif key == 'free':
                available.append({**model, 'key': key, 'available': True})
            else:
                available.append({**model, 'key': key, 'available': False})
        return available
    
    async def generate_response(self, prompt: str, model_key: str = 'free', user=None):
        """Generate AI response using specified model"""
        try:
            model = self.models.get(model_key, self.models['free'])
            
            # Check if user can use this model
            if model_key != 'free' and (not user or not user.is_premium()):
                if not user or user.wallet < model['cost']:
                    return {
                        'success': False,
                        'error': f'Insufficient balance. Need ₹{model["cost"]} for {model["name"]}',
                        'upgrade_required': True
                    }
            
            # Generate response based on provider
            if model['provider'] == 'openai':
                response = await self._openai_request(prompt, model['model_id'])
            elif model['provider'] == 'anthropic':
                response = await self._claude_request(prompt, model['model_id'])
            elif model['provider'] == 'google':
                response = await self._gemini_request(prompt, model['model_id'])
            else:
                response = await self._huggingface_request(prompt, model['model_id'])
            
            if response['success']:
                # Deduct cost from user wallet (if not premium)
                if user and model_key != 'free' and not user.is_premium():
                    user.wallet -= model['cost']
                    user.chats_count += 1
                    
                    # Add earnings to admin
                    admin_earnings = model['cost'] * ADMIN_SHARE
                    user_earnings = model['cost'] * USER_SHARE
                    
                    # Record API usage
                    usage = APIUsage(
                        user_id=user.id,
                        api_type=model_key,
                        model_name=model['name'],
                        cost=model['cost'],
                        earnings_generated=admin_earnings,
                        request_data=prompt[:500],
                        response_data=response['content'][:500]
                    )
                    db.session.add(usage)
                    db.session.commit()
                
                return {
                    'success': True,
                    'content': response['content'],
                    'model': model['name'],
                    'cost': model['cost']
                }
            else:
                return response
                
        except Exception as e:
            log("ai", "ERROR", f"AI generation failed: {e}")
            return {
                'success': False,
                'error': 'AI service temporarily unavailable. Please try again.',
                'fallback': True
            }
    
    async def _openai_request(self, prompt: str, model: str):
        """Make request to OpenAI API"""
        try:
            if not OPENAI_API_KEY:
                return {'success': False, 'error': 'OpenAI API key not configured'}
            
            headers = {
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': model,
                'messages': [
                    {'role': 'system', 'content': 'You are Ganesh AI, a helpful and intelligent assistant created to provide the best possible responses.'},
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 2000,
                'temperature': 0.7
            }
            
            async with httpx.AsyncClient(timeout=OPENAI_TIMEOUT) as client:
                response = await client.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers=headers,
                    json=data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    return {'success': True, 'content': content}
                else:
                    return {'success': False, 'error': f'OpenAI API error: {response.status_code}'}
                    
        except Exception as e:
            return {'success': False, 'error': f'OpenAI request failed: {str(e)}'}
    
    async def _claude_request(self, prompt: str, model: str):
        """Make request to Claude API (placeholder - requires Anthropic API)"""
        # For now, fallback to OpenAI
        return await self._openai_request(prompt, 'gpt-3.5-turbo')
    
    async def _gemini_request(self, prompt: str, model: str):
        """Make request to Gemini API (placeholder - requires Google API)"""
        # For now, fallback to OpenAI
        return await self._openai_request(prompt, 'gpt-3.5-turbo')
    
    async def _huggingface_request(self, prompt: str, model: str):
        """Make request to Hugging Face API"""
        try:
            if not HF_API_TOKEN or not HF_API_URL:
                # Fallback response for free model
                responses = [
                    f"Hello! I'm Ganesh AI. You asked: '{prompt[:50]}...' - I'm here to help you with any questions!",
                    f"Thanks for using Ganesh AI! Regarding '{prompt[:50]}...', I'd be happy to assist you further.",
                    f"Great question about '{prompt[:50]}...'! As Ganesh AI, I'm designed to provide helpful responses.",
                ]
                return {'success': True, 'content': random.choice(responses)}
            
            headers = {'Authorization': f'Bearer {HF_API_TOKEN}'}
            data = {'inputs': prompt}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(HF_API_URL, headers=headers, json=data)
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        content = result[0].get('generated_text', 'No response generated')
                        return {'success': True, 'content': content}
                    else:
                        return {'success': False, 'error': 'Invalid response format'}
                else:
                    return {'success': False, 'error': f'HuggingFace API error: {response.status_code}'}
                    
        except Exception as e:
            # Fallback response
            return {
                'success': True, 
                'content': f"I'm Ganesh AI! You asked about '{prompt[:50]}...' - I'm here to help! For better responses, consider upgrading to premium models."
            }

# Initialize AI Manager
ai_manager = AIModelManager()

# =========================
# 💰 MONETIZATION SYSTEM 💰
# =========================

def track_visit(user_id=None, page='/', referrer=None):
    """Track user visit and generate earnings"""
    try:
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')
        
        # Create visit record
        visit = Visit(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            page=page,
            referrer=referrer,
            earnings_generated=VISIT_PAY_RATE
        )
        db.session.add(visit)
        
        # Add earnings to user if logged in
        if user_id:
            user = User.query.get(user_id)
            if user:
                user.visits_count += 1
                user.last_visit = datetime.utcnow()
                user.add_earnings(VISIT_PAY_RATE, f"Visit earnings for {page}")
        
        # Add earnings to admin (70% of visit earnings)
        admin_user = User.query.filter_by(role='admin').first()
        if admin_user:
            admin_earnings = VISIT_PAY_RATE * ADMIN_SHARE
            admin_user.add_earnings(admin_earnings, f"Admin share from visit to {page}")
        
        db.session.commit()
        log("monetization", "INFO", f"Visit tracked: {page} - Earnings: ₹{VISIT_PAY_RATE}")
        
    except Exception as e:
        log("monetization", "ERROR", f"Visit tracking failed: {e}")

def process_referral(referral_code, new_user_id):
    """Process referral bonus"""
    try:
        referrer = User.query.filter_by(referral_code=referral_code).first()
        if referrer and referrer.id != new_user_id:
            # Add referral bonus to referrer
            referrer.add_earnings(REFERRAL_BONUS, f"Referral bonus for user {new_user_id}")
            referrer.referrals_count += 1
            
            # Create referral record
            referral = Referral(
                referrer_id=referrer.id,
                referred_id=new_user_id,
                referral_code=referral_code,
                bonus_amount=REFERRAL_BONUS
            )
            db.session.add(referral)
            
            # Update referred user
            new_user = User.query.get(new_user_id)
            if new_user:
                new_user.referred_by = referral_code
                # Give welcome bonus to new user
                new_user.add_earnings(REFERRAL_BONUS * 0.1, "Welcome bonus from referral")
            
            db.session.commit()
            log("monetization", "INFO", f"Referral processed: {referral_code} -> User {new_user_id}")
            return True
    except Exception as e:
        log("monetization", "ERROR", f"Referral processing failed: {e}")
    return False

def generate_ad_revenue():
    """Simulate ad revenue generation"""
    try:
        # Simulate ad clicks and impressions
        daily_ad_revenue = random.uniform(50, 200)  # ₹50-200 per day
        
        admin_user = User.query.filter_by(role='admin').first()
        if admin_user:
            admin_user.add_earnings(daily_ad_revenue, "Daily ad revenue")
            db.session.commit()
            log("monetization", "INFO", f"Ad revenue generated: ₹{daily_ad_revenue}")
            
    except Exception as e:
        log("monetization", "ERROR", f"Ad revenue generation failed: {e}")

def query_openai(prompt: str, user_id: Optional[int] = None) -> str:
    """Legacy OpenAI function - now uses AI Manager"""
    try:
        user = User.query.get(user_id) if user_id else None
        
        # Use async AI manager in sync context
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            ai_manager.generate_response(prompt, 'free', user)
        )
        
        if result['success']:
            return result['content']
        else:
            return f"I'm Ganesh AI! I'd love to help you with: '{prompt[:50]}...' Please try again or upgrade for better responses!"
            
    except Exception as e:
        log("ai", "ERROR", f"OpenAI query failed: {e}")
        return f"Hello! I'm Ganesh AI. You asked about '{prompt[:50]}...' - I'm here to help! Please try again."

def query_huggingface(prompt: str, user_id: Optional[int] = None) -> str:
    """Legacy HuggingFace function - now uses AI Manager"""
    return query_openai(prompt, user_id)  # Fallback to unified system

# =========================
# WEB ROUTES
# =========================

@app.route('/')
def index():
    """Modern ChatGPT-style Home Page with Visit Tracking"""
    # Track visit for monetization
    user_id = session.get('user_id')
    track_visit(user_id, '/', request.referrer)
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ app_name }} - World's Most Advanced AI Bot</title>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            
            .navbar {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 1rem 2rem;
                position: fixed;
                top: 0;
                width: 100%;
                z-index: 1000;
                box-shadow: 0 2px 20px rgba(0,0,0,0.1);
            }
            
            .nav-content {
                max-width: 1200px;
                margin: 0 auto;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .logo {
                font-size: 1.5rem;
                font-weight: bold;
                color: #667eea;
                text-decoration: none;
            }
            
            .nav-links {
                display: flex;
                gap: 1rem;
            }
            
            .nav-links a {
                text-decoration: none;
                color: #333;
                padding: 0.5rem 1rem;
                border-radius: 25px;
                transition: all 0.3s ease;
            }
            
            .nav-links a:hover {
                background: #667eea;
                color: white;
            }
            
            .hero {
                padding: 120px 2rem 80px;
                text-align: center;
                color: white;
            }
            
            .hero h1 {
                font-size: 3.5rem;
                margin-bottom: 1rem;
                background: linear-gradient(45deg, #fff, #f0f0f0);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .hero p {
                font-size: 1.2rem;
                margin-bottom: 2rem;
                opacity: 0.9;
            }
            
            .cta-buttons {
                display: flex;
                gap: 1rem;
                justify-content: center;
                flex-wrap: wrap;
                margin-bottom: 3rem;
            }
            
            .btn {
                padding: 1rem 2rem;
                border: none;
                border-radius: 50px;
                font-size: 1rem;
                font-weight: 600;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                transition: all 0.3s ease;
                cursor: pointer;
            }
            
            .btn-primary {
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }
            
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
            }
            
            .btn-secondary {
                background: rgba(255, 255, 255, 0.2);
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            
            .btn-secondary:hover {
                background: rgba(255, 255, 255, 0.3);
                transform: translateY(-2px);
            }
            
            .features {
                background: white;
                padding: 80px 2rem;
            }
            
            .features-container {
                max-width: 1200px;
                margin: 0 auto;
            }
            
            .features h2 {
                text-align: center;
                font-size: 2.5rem;
                margin-bottom: 3rem;
                color: #333;
            }
            
            .features-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 2rem;
            }
            
            .feature-card {
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                padding: 2rem;
                border-radius: 20px;
                text-align: center;
                transition: transform 0.3s ease;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            
            .feature-card:hover {
                transform: translateY(-10px);
            }
            
            .feature-icon {
                font-size: 3rem;
                margin-bottom: 1rem;
                background: linear-gradient(45deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .feature-card h3 {
                font-size: 1.5rem;
                margin-bottom: 1rem;
                color: #333;
            }
            
            .feature-card p {
                color: #666;
                line-height: 1.6;
            }
            
            .stats {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 80px 2rem;
                color: white;
                text-align: center;
            }
            
            .stats-grid {
                max-width: 800px;
                margin: 0 auto;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 2rem;
            }
            
            .stat-item h3 {
                font-size: 2.5rem;
                margin-bottom: 0.5rem;
            }
            
            .stat-item p {
                opacity: 0.9;
            }
            
            .footer {
                background: #2c3e50;
                color: white;
                padding: 2rem;
                text-align: center;
            }
            
            .footer-links {
                display: flex;
                justify-content: center;
                gap: 2rem;
                margin-bottom: 1rem;
                flex-wrap: wrap;
            }
            
            .footer-links a {
                color: white;
                text-decoration: none;
                transition: color 0.3s ease;
            }
            
            .footer-links a:hover {
                color: #667eea;
            }
            
            @media (max-width: 768px) {
                .hero h1 { font-size: 2.5rem; }
                .cta-buttons { flex-direction: column; align-items: center; }
                .nav-links { display: none; }
            }
        </style>
    </head>
    <body>
        <nav class="navbar">
            <div class="nav-content">
                <a href="/" class="logo">🤖 {{ app_name }}</a>
                <div class="nav-links">
                    {% if session.user_id %}
                        <a href="{{ url_for('dashboard') }}"><i class="fas fa-tachometer-alt"></i> Dashboard</a>
                        {% if session.user_role == 'admin' %}
                            <a href="{{ url_for('admin_dashboard') }}"><i class="fas fa-cog"></i> Admin</a>
                        {% endif %}
                        <a href="{{ url_for('logout') }}"><i class="fas fa-sign-out-alt"></i> Logout</a>
                    {% else %}
                        <a href="{{ url_for('login') }}"><i class="fas fa-sign-in-alt"></i> Login</a>
                        <a href="{{ url_for('register') }}"><i class="fas fa-user-plus"></i> Register</a>
                    {% endif %}
                </div>
            </div>
        </nav>

        <section class="hero">
            <h1>🤖 {{ app_name }}</h1>
            <p>World's Most Advanced Money-Making AI Bot</p>
            <p>💰 Earn money with every visit • 🧠 Multiple AI Models • 📱 Telegram Integration</p>
            
            <div class="cta-buttons">
                {% if session.user_id %}
                    <a href="{{ url_for('dashboard') }}" class="btn btn-primary">
                        <i class="fas fa-rocket"></i> Start Chatting
                    </a>
                {% else %}
                    <a href="{{ url_for('register') }}" class="btn btn-primary">
                        <i class="fas fa-rocket"></i> Get Started Free
                    </a>
                    <a href="{{ url_for('login') }}" class="btn btn-secondary">
                        <i class="fas fa-sign-in-alt"></i> Login
                    </a>
                {% endif %}
                <a href="https://t.me/{{ telegram_username }}" target="_blank" class="btn btn-secondary">
                    <i class="fab fa-telegram"></i> Telegram Bot
                </a>
            </div>
        </section>

        <section class="features">
            <div class="features-container">
                <h2>🚀 Powerful Features</h2>
                <div class="features-grid">
                    <div class="feature-card">
                        <div class="feature-icon">🧠</div>
                        <h3>Multiple AI Models</h3>
                        <p>Access GPT-4, Claude, Gemini, and more. Choose the best AI for your needs with intelligent model routing.</p>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon">💰</div>
                        <h3>Earn Money</h3>
                        <p>Get paid for every visit, chat, and referral. Turn your AI usage into real income with our revenue sharing system.</p>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon">📱</div>
                        <h3>Telegram Integration</h3>
                        <p>Chat with our AI bot directly on Telegram. Instant responses, file sharing, and seamless experience.</p>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon">⚡</div>
                        <h3>Lightning Fast</h3>
                        <p>Optimized for speed and performance. Get AI responses in seconds with our advanced infrastructure.</p>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon">🔒</div>
                        <h3>Secure & Private</h3>
                        <p>Your data is encrypted and secure. We prioritize privacy and never share your conversations.</p>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon">📊</div>
                        <h3>Analytics Dashboard</h3>
                        <p>Track your usage, earnings, and performance with detailed analytics and real-time insights.</p>
                    </div>
                </div>
            </div>
        </section>

        <section class="stats">
            <h2>🎯 Platform Statistics</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <h3>{{ total_users }}+</h3>
                    <p>Active Users</p>
                </div>
                <div class="stat-item">
                    <h3>{{ total_chats }}+</h3>
                    <p>AI Conversations</p>
                </div>
                <div class="stat-item">
                    <h3>₹{{ total_earnings }}</h3>
                    <p>Total Earnings</p>
                </div>
                <div class="stat-item">
                    <h3>99.9%</h3>
                    <p>Uptime</p>
                </div>
            </div>
        </section>

        <footer class="footer">
            <div class="footer-links">
                <a href="https://t.me/{{ telegram_username }}" target="_blank">
                    <i class="fab fa-telegram"></i> Telegram Bot
                </a>
                <a href="{{ url_for('admin_dashboard') if session.user_role == 'admin' else '#' }}">
                    <i class="fas fa-cog"></i> Admin Panel
                </a>
                <a href="{{ url_for('dashboard') if session.user_id else url_for('register') }}">
                    <i class="fas fa-tachometer-alt"></i> Web App
                </a>
                <a href="mailto:{{ business_email }}">
                    <i class="fas fa-envelope"></i> Support
                </a>
            </div>
            <p>&copy; 2024 {{ app_name }}. Built with ❤️ for maximum earnings.</p>
            <p>{{ support_username }} • {{ business_email }}</p>
        </footer>

        <script>
            // Add some interactive effects
            document.addEventListener('DOMContentLoaded', function() {
                // Animate stats on scroll
                const stats = document.querySelectorAll('.stat-item h3');
                const observer = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const target = entry.target;
                            const finalValue = target.textContent;
                            target.textContent = '0';
                            
                            // Simple counter animation
                            let current = 0;
                            const increment = parseInt(finalValue.replace(/[^0-9]/g, '')) / 50;
                            const timer = setInterval(() => {
                                current += increment;
                                if (current >= parseInt(finalValue.replace(/[^0-9]/g, ''))) {
                                    target.textContent = finalValue;
                                    clearInterval(timer);
                                } else {
                                    target.textContent = Math.floor(current) + finalValue.replace(/[0-9]/g, '');
                                }
                            }, 50);
                        }
                    });
                });
                
                stats.forEach(stat => observer.observe(stat));
            });
        </script>
    </body>
    </html>
    """, 
    app_name=APP_NAME,
    telegram_username=TELEGRAM_TOKEN.split(':')[0] if TELEGRAM_TOKEN else 'ganeshaibot',
    support_username=SUPPORT_USERNAME,
    business_email=BUSINESS_EMAIL,
    total_users=User.query.count(),
    total_chats=APIUsage.query.count(),
    total_earnings=round(sum([u.total_earned for u in User.query.all()]), 2)
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('register'))
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Register - {{ app_name }}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 400px; margin: 50px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; margin-bottom: 30px; }
            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
            .form-group input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            .btn { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            .btn:hover { background: #0056b3; }
            .links { text-align: center; margin-top: 20px; }
            .links a { color: #007bff; text-decoration: none; }
            .alert { padding: 10px; margin-bottom: 20px; border-radius: 5px; }
            .alert.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .alert.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Register for {{ app_name }}</h2>
            </div>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert {{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form method="POST">
                <div class="form-group">
                    <label for="username">Username:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                
                <div class="form-group">
                    <label for="email">Email:</label>
                    <input type="email" id="email" name="email" required>
                </div>
                
                <div class="form-group">
                    <label for="password">Password:</label>
                    <input type="password" id="password" name="password" required>
                </div>
                
                <button type="submit" class="btn">Register</button>
            </form>
            
            <div class="links">
                <p>Already have an account? <a href="{{ url_for('login') }}">Login here</a></p>
                <p><a href="{{ url_for('index') }}">Back to Home</a></p>
            </div>
        </div>
    </body>
    </html>
    """, app_name=APP_NAME)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return redirect(url_for('login'))
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            
            flash(f'Welcome back, {user.username}!', 'success')
            
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login - {{ app_name }}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 400px; margin: 50px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; margin-bottom: 30px; }
            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
            .form-group input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            .btn { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            .btn:hover { background: #0056b3; }
            .links { text-align: center; margin-top: 20px; }
            .links a { color: #007bff; text-decoration: none; }
            .alert { padding: 10px; margin-bottom: 20px; border-radius: 5px; }
            .alert.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .alert.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Login to {{ app_name }}</h2>
            </div>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert {{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form method="POST">
                <div class="form-group">
                    <label for="username">Username:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                
                <div class="form-group">
                    <label for="password">Password:</label>
                    <input type="password" id="password" name="password" required>
                </div>
                
                <button type="submit" class="btn">Login</button>
            </form>
            
            <div class="links">
                <p>Don't have an account? <a href="{{ url_for('register') }}">Register here</a></p>
                <p><a href="{{ url_for('index') }}">Back to Home</a></p>
            </div>
        </div>
    </body>
    </html>
    """, app_name=APP_NAME)

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Modern ChatGPT-style Dashboard with Visit Tracking"""
    user = User.query.get(session['user_id'])
    
    # Track visit for monetization
    track_visit(user.id, '/dashboard', request.referrer)
    
    # Generate referral code if not exists
    if not user.referral_code:
        user.generate_referral_code()
        db.session.commit()
    
    # Get user's recent data
    transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.created_at.desc()).limit(5).all()
    api_usage = APIUsage.query.filter_by(user_id=user.id).order_by(APIUsage.created_at.desc()).limit(5).all()
    available_models = ai_manager.get_available_models(user)
    
    return render_template('dashboard_new.html',
    app_name=APP_NAME,
    user=user,
    transactions=transactions,
    api_usage=api_usage,
    referral_bonus=REFERRAL_BONUS
    )

@app.route('/admin')
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """Advanced Admin Control Panel"""
    user = User.query.get(session['user_id'])
    
    # Get comprehensive statistics
    stats = {
        'total_users': User.query.count(),
        'total_revenue': db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.transaction_type == 'credit'
        ).scalar() or 0,
        'total_chats': db.session.query(db.func.sum(User.chats_count)).scalar() or 0,
        'active_users': User.query.filter(
            User.last_visit >= datetime.utcnow() - timedelta(days=1)
        ).count(),
        'premium_users': User.query.filter(
            User.premium_until > datetime.utcnow()
        ).count(),
        'pending_withdrawals': WithdrawalRequest.query.filter_by(status='pending').count(),
        'total_earnings': db.session.query(db.func.sum(User.total_earned)).scalar() or 0
    }
    
    return render_template('admin_panel.html',
        app_name=APP_NAME,
        user=user,
        stats=stats,
        domain=DOMAIN,
        current_time=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    )

# =========================
# TELEGRAM BOT SETUP
# =========================

def setup_telegram():
    """Setup advanced Telegram bot system"""
    if not TELEGRAM_TOKEN:
        log("telegram", "WARNING", "Telegram token not configured. Skipping bot setup.")
        return
    
    try:
        # Import the advanced bot system
        from telegram_bot import ganesh_bot, start_telegram_bot
        import threading
        import asyncio
        
        # Start bot in a separate thread
        def start_bot_thread():
            try:
                # Create new event loop for the thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Start the bot
                loop.run_until_complete(start_telegram_bot())
                
            except Exception as e:
                log("telegram", "ERROR", f"Bot thread error: {e}")
        
        # Start bot in background thread
        bot_thread = threading.Thread(target=start_bot_thread, daemon=True)
        bot_thread.start()
        
        log("telegram", "INFO", "Advanced Telegram bot system started successfully")
        
    except ImportError as e:
        log("telegram", "ERROR", f"Telegram bot dependencies not available: {e}")
    except Exception as e:
        log("telegram", "ERROR", f"Failed to setup Telegram bot: {e}")

# Global telegram app instance
telegram_app = None

# =========================
# MAIN APPLICATION STARTUP
# =========================

def migrate_database():
    """Migrate database schema to add missing columns"""
    try:
        from sqlalchemy import inspect, text
        
        # Check if we need to add new columns
        inspector = inspect(db.engine)
        
        # Check if users table exists
        if not inspector.has_table('users'):
            log("database", "INFO", "Users table doesn't exist, will be created by db.create_all()")
            return
            
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        missing_columns = []
        required_columns = [
            'total_earned', 'visits_count', 'chats_count', 'referrals_count',
            'referral_code', 'referred_by', 'premium_until', 'last_visit'
        ]
        
        for col in required_columns:
            if col not in columns:
                missing_columns.append(col)
        
        if missing_columns:
            log("database", "INFO", f"Adding missing columns: {missing_columns}")
            
            # Add missing columns with ALTER TABLE using session.execute
            for col in missing_columns:
                try:
                    if col in ['total_earned']:
                        db.session.execute(text(f"ALTER TABLE users ADD COLUMN {col} FLOAT DEFAULT 0.0"))
                    elif col in ['visits_count', 'chats_count', 'referrals_count']:
                        db.session.execute(text(f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT 0"))
                    elif col in ['referral_code', 'referred_by']:
                        db.session.execute(text(f"ALTER TABLE users ADD COLUMN {col} VARCHAR(20)"))
                    elif col in ['premium_until', 'last_visit']:
                        db.session.execute(text(f"ALTER TABLE users ADD COLUMN {col} DATETIME"))
                    
                    log("database", "INFO", f"Added column: {col}")
                except Exception as e:
                    log("database", "WARNING", f"Could not add column {col}: {e}")
            
            # Commit changes
            db.session.commit()
            log("database", "INFO", "Database migration completed")
        else:
            log("database", "INFO", "Database schema is up to date")
            
    except Exception as e:
        log("database", "ERROR", f"Database migration failed: {e}")
        # If migration fails, recreate tables
        try:
            log("database", "INFO", "Attempting to recreate database tables...")
            db.drop_all()
            db.create_all()
            log("database", "INFO", "Database recreated successfully")
        except Exception as e2:
            log("database", "ERROR", f"Database recreation failed: {e2}")

# =========================
# API ROUTES FOR FRONTEND
# =========================

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """Handle chat messages from frontend"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        model = data.get('model', 'ganesh-free')
        conversation_id = data.get('conversation_id')
        
        if not message:
            return jsonify({'success': False, 'message': 'Message is required'})
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Check if premium model and user has access
        premium_models = ['gpt-4-turbo', 'claude-3-sonnet', 'gemini-pro']
        if model in premium_models:
            if not user.premium_until or user.premium_until < datetime.utcnow():
                return jsonify({
                    'success': False, 
                    'message': 'Premium subscription required for this model',
                    'premium_required': True
                })
        
        # Generate AI response based on model
        response = generate_ai_response(message, model, user)
        
        # Track chat for monetization
        track_chat(user.id, message, response, model)
        
        # Update user stats
        user.chats_count = (user.chats_count or 0) + 1
        user.add_earnings(CHAT_PAY_RATE, f"Chat with {model}")
        db.session.commit()
        
        # Return response with updated stats
        return jsonify({
            'success': True,
            'response': response,
            'model': model,
            'stats': {
                'wallet': float(user.wallet),
                'chats_count': user.chats_count,
                'total_earned': float(user.total_earned)
            }
        })
        
    except Exception as e:
        log("api", "ERROR", f"Chat API error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'})

def generate_ai_response(message, model, user):
    """Generate AI response based on selected model"""
    try:
        # Free model - simple responses
        if model == 'ganesh-free':
            return generate_free_response(message, user)
        
        # Premium models - use external APIs
        elif model == 'gpt-4-turbo':
            return generate_gpt4_response(message, user)
        
        elif model == 'claude-3-sonnet':
            return generate_claude_response(message, user)
        
        elif model == 'gemini-pro':
            return generate_gemini_response(message, user)
        
        else:
            return generate_free_response(message, user)
            
    except Exception as e:
        log("ai", "ERROR", f"AI response generation failed: {e}")
        return "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."

def generate_free_response(message, user):
    """Generate response for free model"""
    message_lower = message.lower()
    
    # Greeting responses
    if any(word in message_lower for word in ['hello', 'hi', 'hey', 'namaste']):
        return f"Hello {user.username}! 👋 I'm Ganesh AI, your intelligent assistant. How can I help you today?"
    
    # Help responses
    elif any(word in message_lower for word in ['help', 'what can you do', 'features']):
        return """I can help you with:
        
🧠 **Intelligent Conversations** - Chat about any topic
📝 **Content Creation** - Writing, essays, stories
🔧 **Problem Solving** - Technical and general problems  
💡 **Creative Ideas** - Brainstorming and inspiration
📚 **Learning Assistance** - Explanations and tutorials
💼 **Business Advice** - Strategy and planning
🎯 **Goal Setting** - Personal and professional goals

For advanced features like GPT-4, Claude, or Gemini, upgrade to Premium! 🚀"""
    
    # About responses
    elif any(word in message_lower for word in ['about', 'who are you', 'what are you']):
        return f"""I'm **Ganesh AI** 🤖, your advanced AI assistant created by {BUSINESS_NAME}.

✨ **What makes me special:**
- 🧠 Intelligent conversations on any topic
- 💡 Creative problem-solving abilities  
- 📚 Vast knowledge base
- 🎯 Personalized responses
- 💰 Earn money while chatting!

**Current Stats:**
- 💬 Chats: {user.chats_count or 0}
- 💰 Earned: ₹{user.total_earned or 0:.2f}
- 👥 Referrals: {user.referrals_count or 0}

Upgrade to Premium for access to GPT-4, Claude, and Gemini! 🚀"""
    
    # Earnings/money related
    elif any(word in message_lower for word in ['earn', 'money', 'payment', 'withdraw']):
        return f"""💰 **Earning with Ganesh AI:**

**Your Current Stats:**
- 💰 Wallet Balance: ₹{user.wallet:.2f}
- 📈 Total Earned: ₹{user.total_earned:.2f}
- 💬 Chat Earnings: ₹{(user.chats_count or 0) * CHAT_PAY_RATE:.2f}
- 👥 Referral Earnings: ₹{(user.referrals_count or 0) * REFERRAL_BONUS:.2f}

**How to Earn More:**
- 💬 Chat with me (₹{CHAT_PAY_RATE} per chat)
- 🔗 Refer friends (₹{REFERRAL_BONUS} per referral)
- 👀 Daily visits (₹{VISIT_PAY_RATE} per visit)

**Withdrawal:** Minimum ₹100 to your bank account
**Referral Code:** {user.referral_code}

Keep chatting to earn more! 🚀"""
    
    # Technical questions
    elif any(word in message_lower for word in ['code', 'programming', 'python', 'javascript', 'html']):
        return """👨‍💻 **Programming & Development:**

I can help you with:
- 🐍 Python programming
- 🌐 Web development (HTML, CSS, JavaScript)
- 📱 Mobile app development
- 🗄️ Database design
- 🔧 Debugging and troubleshooting
- 📚 Learning resources and tutorials

**Example:** "Write a Python function to calculate fibonacci numbers"

For advanced coding assistance with detailed explanations, try our Premium models like GPT-4! 🚀"""
    
    # Business related
    elif any(word in message_lower for word in ['business', 'startup', 'marketing', 'strategy']):
        return """💼 **Business & Entrepreneurship:**

I can assist with:
- 🚀 Startup ideas and validation
- 📊 Business planning and strategy
- 📈 Marketing and growth tactics
- 💰 Financial planning
- 🎯 Market research
- 👥 Team building advice

**Current Business Opportunity:** 
Earn money by using our AI platform! You've already earned ₹{user.total_earned:.2f}

For detailed business analysis and advanced strategies, upgrade to Premium! 💎"""
    
    # Creative requests
    elif any(word in message_lower for word in ['story', 'poem', 'creative', 'write']):
        return """✨ **Creative Writing & Content:**

I can create:
- 📖 Stories and narratives
- 🎭 Poems and verses  
- ✍️ Articles and blogs
- 📝 Essays and reports
- 🎨 Creative content ideas
- 📱 Social media posts

**Example:** "Write a short story about AI and humans"

For premium creative content with advanced storytelling, try Claude 3 Sonnet! 🎨"""
    
    # Default intelligent response
    else:
        responses = [
            f"That's an interesting question, {user.username}! Let me think about that...",
            f"Great question! Based on what you're asking about '{message[:50]}{'...' if len(message) > 50 else ''}'",
            f"I understand you're asking about this topic. Here's my perspective...",
            f"Thanks for sharing that with me, {user.username}. Let me help you with this...",
        ]
        
        import random
        base_response = random.choice(responses)
        
        # Add contextual response based on message content
        if '?' in message:
            return f"""{base_response}

While I can provide basic assistance with your question, for more detailed and accurate responses, I recommend upgrading to our Premium models:

🚀 **GPT-4 Turbo** - Most advanced reasoning
🎨 **Claude 3 Sonnet** - Creative and analytical  
🧠 **Gemini Pro** - Google's latest AI

**Your Progress:**
- 💬 Chats: {user.chats_count or 0} (Earned: ₹{(user.chats_count or 0) * CHAT_PAY_RATE:.2f})
- 💰 Total Earned: ₹{user.total_earned:.2f}

Keep chatting to earn more! Each message earns you ₹{CHAT_PAY_RATE}! 💰"""
        
        else:
            return f"""{base_response}

I'm here to help with any questions or tasks you have! As your AI assistant, I can:

🧠 Answer questions and provide explanations
💡 Help with creative projects and ideas
🔧 Assist with problem-solving
📚 Provide learning resources

**Earning Update:** You just earned ₹{CHAT_PAY_RATE} for this chat! 
**Total Earned:** ₹{user.total_earned:.2f}

What would you like to explore next? 🚀"""

def generate_gpt4_response(message, user):
    """Generate GPT-4 response (placeholder for actual API integration)"""
    return f"""🚀 **GPT-4 Turbo Response:**

Hello {user.username}! I'm processing your message with GPT-4's advanced capabilities.

**Your Message:** "{message}"

**Advanced Analysis:** This is where GPT-4 would provide a sophisticated, detailed response with:
- Deep contextual understanding
- Multi-step reasoning
- Comprehensive explanations
- Creative problem-solving

*Note: This is a demo response. In production, this would connect to OpenAI's GPT-4 API for real responses.*

**Premium Benefits Active:**
- ✅ Advanced AI models
- ✅ Detailed responses  
- ✅ Priority processing
- ✅ Unlimited chats

Keep exploring with Premium! 💎"""

def generate_claude_response(message, user):
    """Generate Claude response (placeholder for actual API integration)"""
    return f"""🎨 **Claude 3 Sonnet Response:**

Greetings {user.username}! I'm Claude, known for thoughtful and nuanced responses.

**Your Inquiry:** "{message}"

**Thoughtful Analysis:** Claude would provide:
- Balanced perspectives
- Creative insights
- Ethical considerations
- Well-structured explanations

*Note: This is a demo response. In production, this would connect to Anthropic's Claude API.*

**Premium Features:**
- 🎭 Creative writing excellence
- 🧠 Analytical thinking
- ⚖️ Balanced viewpoints
- 📚 Comprehensive knowledge

Your Premium subscription is enhancing your AI experience! ✨"""

def generate_gemini_response(message, user):
    """Generate Gemini response (placeholder for actual API integration)"""
    return f"""🧠 **Gemini Pro Response:**

Hello {user.username}! Google's Gemini Pro is analyzing your request.

**Processing:** "{message}"

**Advanced Capabilities:** Gemini Pro offers:
- Multi-modal understanding
- Real-time information
- Advanced reasoning
- Google's latest AI technology

*Note: This is a demo response. In production, this would connect to Google's Gemini API.*

**Premium Advantage:**
- 🌐 Latest AI technology
- 🔍 Enhanced accuracy
- ⚡ Fast processing
- 🎯 Precise responses

Experience the future of AI with Premium! 🚀"""

@app.route('/api/user/stats', methods=['GET'])
@login_required
def api_user_stats():
    """Get current user statistics"""
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        return jsonify({
            'success': True,
            'stats': {
                'wallet': float(user.wallet),
                'total_earned': float(user.total_earned),
                'chats_count': user.chats_count or 0,
                'visits_count': user.visits_count or 0,
                'referrals_count': user.referrals_count or 0,
                'is_premium': user.premium_until and user.premium_until > datetime.utcnow()
            }
        })
    except Exception as e:
        log("api", "ERROR", f"Stats API error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'})

@app.route('/api/withdrawal', methods=['POST'])
@login_required
def api_withdrawal():
    """Handle withdrawal requests"""
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        if amount < 100:
            return jsonify({'success': False, 'message': 'Minimum withdrawal amount is ₹100'})
        
        if amount > user.wallet:
            return jsonify({'success': False, 'message': 'Insufficient balance'})
        
        # Create withdrawal request
        withdrawal = WithdrawalRequest(
            user_id=user.id,
            amount=amount,
            status='pending'
        )
        
        # Deduct from wallet
        user.wallet -= amount
        
        db.session.add(withdrawal)
        db.session.commit()
        
        log("withdrawal", "INFO", f"Withdrawal request: User {user.username}, Amount: ₹{amount}")
        
        return jsonify({
            'success': True,
            'message': 'Withdrawal request submitted successfully!',
            'new_balance': float(user.wallet)
        })
        
    except Exception as e:
        log("api", "ERROR", f"Withdrawal API error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'})

@app.route('/api/subscribe', methods=['POST'])
@login_required
def api_subscribe():
    """Handle premium subscription"""
    try:
        data = request.get_json()
        plan = data.get('plan', 'monthly')
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Calculate amount and duration
        if plan == 'monthly':
            amount = PREMIUM_MONTHLY
            duration_days = 30
        elif plan == 'yearly':
            amount = PREMIUM_YEARLY
            duration_days = 365
        else:
            return jsonify({'success': False, 'message': 'Invalid plan'})
        
        # Create payment URL (placeholder for Cashfree integration)
        payment_url = f"/payment/premium?plan={plan}&amount={amount}&user_id={user.id}"
        
        return jsonify({
            'success': True,
            'payment_url': payment_url,
            'amount': amount,
            'plan': plan
        })
        
    except Exception as e:
        log("api", "ERROR", f"Subscribe API error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'})

@app.route('/api/log-error', methods=['POST'])
def api_log_error():
    """Log frontend errors for analysis"""
    try:
        data = request.get_json()
        error_info = {
            'error': data.get('error'),
            'stack': data.get('stack'),
            'timestamp': data.get('timestamp'),
            'user_agent': data.get('userAgent'),
            'url': data.get('url'),
            'user_id': session.get('user_id')
        }
        
        log("frontend_error", "ERROR", f"Frontend error: {error_info}")
        
        return jsonify({'success': True})
    except:
        return jsonify({'success': False})

# Admin API Routes
@app.route('/api/admin/stats', methods=['GET'])
@login_required
@admin_required
def api_admin_stats():
    """Get admin dashboard statistics"""
    try:
        # Get comprehensive statistics
        stats = {
            'total_users': User.query.count(),
            'total_revenue': db.session.query(db.func.sum(Transaction.amount)).filter(
                Transaction.transaction_type == 'credit'
            ).scalar() or 0,
            'total_chats': db.session.query(db.func.sum(User.chats_count)).scalar() or 0,
            'active_users': User.query.filter(
                User.last_visit >= datetime.utcnow() - timedelta(days=1)
            ).count(),
            'premium_users': User.query.filter(
                User.premium_until > datetime.utcnow()
            ).count(),
            'pending_withdrawals': WithdrawalRequest.query.filter_by(status='pending').count(),
            'total_earnings': db.session.query(db.func.sum(User.total_earned)).scalar() or 0,
            'today_revenue': db.session.query(db.func.sum(Transaction.amount)).filter(
                Transaction.transaction_type == 'credit',
                Transaction.created_at >= datetime.utcnow().date()
            ).scalar() or 0,
            'month_revenue': db.session.query(db.func.sum(Transaction.amount)).filter(
                Transaction.transaction_type == 'credit',
                Transaction.created_at >= datetime.utcnow().replace(day=1)
            ).scalar() or 0
        }
        
        # Get recent activity
        recent_activity = []
        recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()
        
        for txn in recent_transactions:
            user = User.query.get(txn.user_id)
            recent_activity.append({
                'time': txn.created_at.isoformat(),
                'user': user.username if user else 'Unknown',
                'action': txn.description or f"{txn.transaction_type.title()} Transaction",
                'amount': float(txn.amount),
                'status': 'success' if txn.status == 'completed' else 'pending'
            })
        
        return jsonify({
            'success': True,
            'stats': stats,
            'recent_activity': recent_activity
        })
        
    except Exception as e:
        log("admin", "ERROR", f"Admin stats API error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get statistics'})

@app.route('/api/admin/users', methods=['GET'])
@login_required
@admin_required
def api_admin_users():
    """Get all users for admin panel"""
    user = User.query.get(session['user_id'])
    if not user or user.role != 'admin':
        return jsonify({'success': False, 'message': 'Admin access required'})
    
    try:
        users = User.query.all()
        users_data = []
        
        for u in users:
            users_data.append({
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'wallet': float(u.wallet),
                'total_earned': float(u.total_earned),
                'chats_count': u.chats_count or 0,
                'referrals_count': u.referrals_count or 0,
                'is_active': u.is_active,
                'created_at': u.created_at.isoformat() if u.created_at else None
            })
        
        return jsonify({
            'success': True,
            'users': users_data
        })
        
    except Exception as e:
        log("api", "ERROR", f"Admin users API error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'})

@app.route('/api/admin/revenue', methods=['GET'])
@login_required
def api_admin_revenue():
    """Get revenue statistics for admin"""
    user = User.query.get(session['user_id'])
    if not user or user.role != 'admin':
        return jsonify({'success': False, 'message': 'Admin access required'})
    
    try:
        # Calculate revenue statistics
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        total_earned = db.session.query(db.func.sum(User.total_earned)).scalar() or 0
        
        # Today's revenue (placeholder calculation)
        today = datetime.utcnow().date()
        today_revenue = total_earned * 0.1  # Placeholder calculation
        
        return jsonify({
            'success': True,
            'total_revenue': float(total_earned),
            'today_revenue': float(today_revenue),
            'total_users': total_users,
            'active_users': active_users
        })
        
    except Exception as e:
        log("api", "ERROR", f"Admin revenue API error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'})

@app.route('/api/admin/bot/<action>', methods=['POST'])
@login_required
def api_admin_bot(action):
    """Control Telegram bot"""
    user = User.query.get(session['user_id'])
    if not user or user.role != 'admin':
        return jsonify({'success': False, 'message': 'Admin access required'})
    
    try:
        if action == 'start':
            # Start bot logic here
            message = "Bot started successfully"
        elif action == 'stop':
            # Stop bot logic here  
            message = "Bot stopped successfully"
        else:
            return jsonify({'success': False, 'message': 'Invalid action'})
        
        log("admin", "INFO", f"Bot {action} by {user.username}")
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        log("api", "ERROR", f"Admin bot API error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'})

# =========================
# PAYMENT API ROUTES
# =========================

@app.route('/api/payment/create', methods=['POST'])
@login_required
def create_payment():
    """Create payment order"""
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        purpose = data.get('purpose', 'wallet_topup')
        
        if amount < 10:
            return jsonify({'success': False, 'message': 'Minimum amount is ₹10'})
        
        # Import payment system
        from cashfree_integration import create_payment_order
        
        result = create_payment_order(session['user_id'], amount, purpose)
        return jsonify(result)
        
    except Exception as e:
        log("payment", "ERROR", f"Payment creation error: {e}")
        return jsonify({'success': False, 'message': 'Payment creation failed'})

@app.route('/api/payment/verify/<order_id>')
@login_required
def verify_payment_status(order_id):
    """Verify payment status"""
    try:
        from cashfree_integration import verify_payment
        
        result = verify_payment(order_id)
        return jsonify(result)
        
    except Exception as e:
        log("payment", "ERROR", f"Payment verification error: {e}")
        return jsonify({'success': False, 'message': 'Verification failed'})

@app.route('/payment/webhook', methods=['POST'])
def payment_webhook():
    """Handle Cashfree webhook"""
    try:
        webhook_data = request.get_json()
        signature = request.headers.get('X-Webhook-Signature', '')
        
        from cashfree_integration import process_webhook
        
        result = process_webhook(webhook_data, signature)
        
        if result['success']:
            return jsonify({'status': 'OK'})
        else:
            return jsonify({'status': 'ERROR'}), 400
            
    except Exception as e:
        log("payment", "ERROR", f"Webhook error: {e}")
        return jsonify({'status': 'ERROR'}), 500

@app.route('/api/payment/methods')
@login_required
def get_payment_methods():
    """Get available payment methods"""
    try:
        from cashfree_integration import get_payment_methods
        
        methods = get_payment_methods()
        return jsonify({'success': True, 'methods': methods})
        
    except Exception as e:
        log("payment", "ERROR", f"Payment methods error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get payment methods'})

@app.route('/api/withdrawal/create', methods=['POST'])
@login_required
def create_withdrawal():
    """Create withdrawal request"""
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        bank_details = data.get('bank_details', {})
        
        if amount < 100:
            return jsonify({'success': False, 'message': 'Minimum withdrawal is ₹100'})
        
        # Validate bank details
        required_fields = ['account_number', 'ifsc_code', 'account_holder_name']
        for field in required_fields:
            if not bank_details.get(field):
                return jsonify({'success': False, 'message': f'Missing {field}'})
        
        from cashfree_integration import create_withdrawal
        
        result = create_withdrawal(session['user_id'], amount, bank_details)
        return jsonify(result)
        
    except Exception as e:
        log("payment", "ERROR", f"Withdrawal creation error: {e}")
        return jsonify({'success': False, 'message': 'Withdrawal request failed'})

@app.route('/api/transactions')
@login_required
def get_transactions():
    """Get user transaction history"""
    try:
        limit = int(request.args.get('limit', 50))
        
        from cashfree_integration import get_transaction_history
        
        history = get_transaction_history(session['user_id'], limit)
        return jsonify({'success': True, 'transactions': history})
        
    except Exception as e:
        log("payment", "ERROR", f"Transaction history error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get transactions'})

@app.route('/payment/success')
def payment_success():
    """Payment success page"""
    order_id = request.args.get('order_id')
    
    if order_id:
        # Verify payment status
        from cashfree_integration import verify_payment
        result = verify_payment(order_id)
        
        if result.get('success') and result.get('status') == 'PAID':
            flash('Payment successful! Your account has been updated.', 'success')
        else:
            flash('Payment verification pending. Please check back in a few minutes.', 'info')
    
    return redirect(url_for('dashboard'))

@app.route('/payment/failed')
def payment_failed():
    """Payment failed page"""
    flash('Payment failed. Please try again or contact support.', 'error')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    log("system", "INFO", f"🚀 Starting {APP_NAME}...")
    
    # Initialize database
    with app.app_context():
        try:
            db.create_all()
            log("database", "INFO", "Database tables created successfully")
            
            # Run database migration
            migrate_database()
            
            # Create admin user if not exists
            admin_user = User.query.filter_by(username=ADMIN_USER).first()
            if not admin_user:
                admin_user = User(
                    username=ADMIN_USER,
                    email=BUSINESS_EMAIL,
                    role='admin'
                )
                admin_user.set_password(ADMIN_PASS)
                admin_user.generate_referral_code()
                db.session.add(admin_user)
                db.session.commit()
                log("admin", "INFO", f"Admin user '{ADMIN_USER}' created successfully")
            else:
                log("admin", "INFO", f"Admin user '{ADMIN_USER}' already exists")
                
        except Exception as e:
            log("database", "ERROR", f"Database initialization failed: {e}")
    
    # Setup Telegram bot (disabled for now to focus on web app)
    log("telegram", "INFO", "Telegram bot setup skipped for web-only deployment")
    
    # Start Flask application
    port = int(os.getenv('PORT', 10000))
    host = os.getenv('HOST', '0.0.0.0')
    
    log("system", "INFO", f"🌐 {APP_NAME} starting on {host}:{port}")
    log("system", "INFO", f"🔗 Web App: {DOMAIN}")
    log("system", "INFO", f"👨‍💼 Admin Panel: {DOMAIN}/admin")
    log("system", "INFO", f"📱 Telegram Bot: https://t.me/{TELEGRAM_TOKEN.split(':')[0] if TELEGRAM_TOKEN else 'Not configured'}")
    
    app.run(
        host=host,
        port=port,
        debug=DEBUG,
        threaded=True
    )
